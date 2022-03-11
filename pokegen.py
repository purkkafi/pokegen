#!/usr/bin/python3

import json
import random
import pprint
import re
import math
import sys
from numpy import random as nprandom
from collections import defaultdict, namedtuple
from enum import Enum, auto

if(len(sys.argv) != 2):
    print('usage: pokegen.py [path to pokefirered folder]')
    exit()

pokered_folder = sys.argv[1]

with open('archetypes.json') as f:
    rawdb = json.load(f)
    archetypes = rawdb['archetypes']
    subarchetypes = rawdb['subarchetypes']
    themedata = rawdb['themes']
    themedata.update(archetypes)
    themedata.update(subarchetypes)
    
    archetypes = list(archetypes.keys())
    subarchetypes = list(subarchetypes.keys())
    type_weights = rawdb['type_weights']
    type_bst_spreads = rawdb['type_bst_spreads']
    evo_stones_for_types = rawdb['evo_stones_for_types']
    move_value_adjustment = rawdb['move_value_adjustment']
    status_move_usage_hints = rawdb['status_move_usage_hints']
    similar_move_sets = rawdb['similar_move_sets']
    tm_list = rawdb['tm_list']
    tutor_move_list = rawdb['tutor_move_list']
    universal_tms = rawdb['universal_tms']
    type_colors = rawdb['type_colors']
    average_weights = rawdb['average_weights']
    average_heights = rawdb['average_heights']
    generic_baby_namestrings = rawdb['generic_baby_namestrings']

# adjust type weights a bit for now
min_weight = min(type_weights.values())
max_weight = max(type_weights.values())
avg_weight = (min_weight + max_weight)/2

for key in type_weights.keys():
    type_weights[key] = (type_weights[key] + 2*avg_weight)/3

# generate normalized bst comparaisons between types
def make_normalized_bsts():
    type_bsts = {}
    
    for tp in type_bst_spreads.keys():
        type_bsts[tp] = sum(type_bst_spreads[tp])
    
    min_val = min(type_bsts.values())
    max_val = max(type_bsts.values())
    diff = max_val - min_val
    
    for tp in type_bsts.keys():
        type_bsts[tp] = (type_bsts[tp]-min_val) / diff
    
    return type_bsts

type_bsts = make_normalized_bsts()

class Flags(Enum):
    SINGLE = auto()
    TWO_STAGES = auto()
    THREE_STAGES = auto()
    LAST_EVOLVABLE_STAGE = auto()
    GRASS_STARTER = auto()
    FIRE_STARTER = auto()
    WATER_STARTER = auto()
    LEGENDARY = auto()
    PSEUDO = auto()
    MYTHICAL = auto()
    LEGENDARY_TRIO = auto()
    FOSSIL = auto()
    DITTO = auto()
    
    def __repr__(self):
        return self.name

LevelEvo = namedtuple('LevelEvo', ['level'])
FriendshipEvo = namedtuple('FriendshipEvo', [])
StoneEvo = namedtuple('StoneEvo', ['stone'])

FRIENDSHIP_EVO_CHANCE = 0.1
STONE_EVO_CHANCE = 0.2

def take_random(ls):
    elem = random.choice(ls)
    ls.remove(elem)
    return elem

MORE_THAN_4_SUCC_VOWELS = re.compile('[aeuio]{4,}')
MORE_THAN_4_SUCC_CONSONANTS = re.compile('[qwrtpsdfghjklzxcvbnm]{4,}')

MORE_THAN_3_END_VOWELS = re.compile('[aeuio]{3,}')
MORE_THAN_3_END_CONSONANTS = re.compile('[qwrtpsdfghjklzxcvbnm]{3,}')

MORE_THAN_3_SUCC_SAME_CHARS = re.compile('(.)\1{2,}')

PREVIOUS_NAME_STARTS = set()

ALL_NAMESTRINGS = set()

for theme in themedata:
    if 'namestrings' in themedata[theme]:
        ALL_NAMESTRINGS.update(themedata[theme]['namestrings'])
    if 'namestrings_baby' in themedata[theme]:
        ALL_NAMESTRINGS.update(themedata[theme]['namestrings_baby'])
ALL_NAMESTRINGS.update(generic_baby_namestrings)

Move = namedtuple('Move', ['name', 'type', 'value', 'damaging', 'power', 'effect'])

def read_move_data():
    with open(pokered_folder + '/src/data/battle_moves.h') as f:
        moves_h = f.read()
    
    chunk_extractor = re.compile('\[MOVE_(.+)\]\s=\n\s\s\s\s{([\s\S]+?)}')
    
    get_type = re.compile('type\s=\sTYPE_([A-Z]+)')
    get_power = re.compile('power\s=\s([0-9]+)')
    get_pp = re.compile('pp\s=\s([0-9]+)')
    get_effect = re.compile('effect\s=\sEFFECT_([A-Z0-9_]+)')
    get_accuracy = re.compile('accuracy\s=\s([0-9]+)')
    
    move_data = {}
    
    for chunk in chunk_extractor.findall(moves_h):
        name = chunk[0]
        data = chunk[1]
        
        if name == 'NONE':
            continue
        
        move_type = get_type.search(data)[1]
        move_power = int(get_power.search(data)[1])
        move_pp = int(get_pp.search(data)[1])
        move_effect = get_effect.search(data)[1]
        move_accuracy = int(get_accuracy.search(data)[1])
        
        if move_power == 0:
            move_value = 30 + (40 - move_pp)*2
        else:
            move_value = move_power + (40 - move_pp)
        
        #if move_accuracy != 0:
        #    move_value = int(move_value * move_accuracy / 100)
        
        move_value = move_value + int(move_value_adjustment[move_effect])
        
        is_damaging = move_power != 0 and move_power != 1
        if move_effect == 'SNORE':
            is_damaging = False
        
        move_data[name] = Move(name=name, type=move_type, value=move_value, damaging=is_damaging, power=move_power, effect=move_effect)
    
    return move_data

def sort_move_list(ls):
    ls = list(ls)
    ls.sort(key=lambda m: m.value)
    return ls

move_data = read_move_data()

class Pokemon:

    def __init__(self, bst_range = (0, 0), flags=set()):
        self.initial_themes = None
        self.themes = set()
        self.types = None
        self.abilities = None
        self.moves = None
        self.bst_range = bst_range
        self.bst = 0
        self.stat_spread_weights = None
        self.evo_target = None
        self.evo_type = None
        self.flags = flags
        self.previous_stage = None
        self.catch_rate = None
        self.egg_cycles = None
        self.base_friendship = None
        self.growth_rate = None
        self.flee_rate = None
        self.tms = None
        self.tutor_moves = None
        self.egg_moves = None
        self.image_colors = None
        self.body_color = None
        self.category = None
        self.weight = None
        self.height = None
    
    def __repr__(self):
        return f'[{self.name}]'
    
    # Recursively adds themes from initially defined ones
    def populate_themes(self):
        self.initial_themes = list(self.themes)
        for theme in self.initial_themes:
            self.populate_theme(theme)
            
    def populate_theme(self, theme):
        self.themes.add(theme)
        
        data = themedata[theme]
        if 'necessary_subthemes' in data:
            for necessary_theme in data['necessary_subthemes']:
                self.populate_theme(necessary_theme)
        
        if 'possible_subthemes' in data:
            #possible_theme = random.choice(data['possible_subthemes'])
            possible_theme = weighted_pick_theme(data['possible_subthemes'])
            self.populate_theme(possible_theme)
        
        if 'optional_subthemes' in data:
            for optional_theme in data['optional_subthemes']:
                if random.random() > 0.5:
                    self.populate_theme(optional_theme)
    
    # Generates data based on themes
    def generate(self):
        self.populate_themes()
        self.generate_name()
        self.generate_type()
        self.generate_bst()
        self.generate_abilities()
        self.generate_egg_groups()
        self.generate_moves()
        self.generate_learnset()
        self.assign_base_stats()
        self.generate_catch_rate()
        self.generate_defeat_yield()
        self.generate_held_items()
        self.generate_gender_ratio()
        self.generate_egg_cycles()
        self.generate_base_friendship()
        self.generate_growth_rate()
        self.generate_flee_rate()
        self.generate_tms()
        self.generate_egg_moves()
        self.generate_image_colors()
        self.generate_dex_data()
    
    def evolve(self, bst_increase = 0):
        next_stage = Pokemon()
        next_stage.previous_stage = self
        next_stage.themes = self.themes
        next_stage.initial_themes = self.initial_themes
        next_stage.flags = set(self.flags)
        
        next_stage.generate_name()
        
        # higher stage might get longer name
        if len(next_stage.name) < len(self.name):
            longest = next_stage.name
            longest_start = next_stage.name_start
            longest_end = next_stage.name_end
            
            for i in range(0,9):
                next_stage.generate_name()
                
                if len(next_stage.name) >= len(self.name):
                    break
                
                if len(next_stage.name) > len(longest):
                    longest = next_stage.name
                    longest_start = next_stage.name_start
                    longest_end = next_stage.name_end
            else:
                next_stage.name = longest
                next_stage.name_start = longest_start
                next_stage.name_end = longest_end
        
        next_stage.types = list(self.types)
        next_stage.abilities = list(self.abilities)
        next_stage.egg_groups = list(self.egg_groups)
        next_stage.moves = self.moves
        next_stage.learnset = list(self.learnset)
        
        next_stage.bst = self.bst + bst_increase
        next_stage.stat_spread_weights = list(self.stat_spread_weights)
        next_stage.assign_base_stats()
        
        next_stage.generate_catch_rate()
        next_stage.generate_defeat_yield()
        next_stage.generate_held_items()
        next_stage.gender_ratio = self.gender_ratio
        next_stage.egg_cycles = self.egg_cycles
        next_stage.base_friendship = self.base_friendship
        next_stage.growth_rate = self.growth_rate
        next_stage.generate_flee_rate()
        next_stage.generate_tms()
        next_stage.generate_image_colors()
        next_stage.generate_dex_data()
        
        if Flags.LAST_EVOLVABLE_STAGE in self.flags:
            next_stage.flags.remove(Flags.LAST_EVOLVABLE_STAGE)
        
        if Flags.THREE_STAGES in self.flags and Flags.LAST_EVOLVABLE_STAGE not in self.flags:
            next_stage.flags.add(Flags.LAST_EVOLVABLE_STAGE)
        
        self.evo_target = next_stage
        self.evo_type = LevelEvo(round(10 + random.randint(0,10) + 40 * ((self.bst-200)/300) ))
        
        if Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags:
            if Flags.LAST_EVOLVABLE_STAGE in self.flags:
                self.evo_type = LevelEvo(random.randint(30,36))
            else:
                self.evo_type = LevelEvo(random.randint(14,18))
            
        elif Flags.LAST_EVOLVABLE_STAGE in self.flags:
            rnd = random.random()
            
            if rnd < FRIENDSHIP_EVO_CHANCE and self.evo_type.level <= 30:
                self.evo_type = FriendshipEvo()
            else:
                rnd = rnd - FRIENDSHIP_EVO_CHANCE
                
                if rnd < STONE_EVO_CHANCE:
                    stones = []
                    if self.types[0] in evo_stones_for_types:
                        stones.extend(evo_stones_for_types[self.types[0]])
                    if self.types[1] in evo_stones_for_types:
                        stones.extend(evo_stones_for_types[self.types[1]])
                    
                    if len(stones) != 0:
                        self.evo_type = StoneEvo(stone=random.choice(stones))
        
        next_stage.evo_adjust_learnset_levels()
        
        return next_stage
    
    def generate_catch_rate(self):
        if Flags.WATER_STARTER in self.flags or Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags:
            self.catch_rate = 45
        elif Flags.MYTHICAL in self.flags or Flags.LEGENDARY in self.flags or Flags.LEGENDARY_TRIO in self.flags:
            self.catch_rate = 3
        else:
            lo = 0
            hi = 300
            nbst = (self.bst-200)/400
            self.catch_rate = round(nbst*lo + (1-nbst)*hi)
            
            if self.catch_rate > 255:
                self.catch_rate = 255
            if self.catch_rate < 45:
                self.catch_rate = 45
    
    def generate_bst(self):
        min_val = self.bst_range[0]
        max_val = self.bst_range[1]
        
        adjust = (type_bsts[self.types[0]] + type_bsts[self.types[1]]) / 2
        r = random.random()*0.8
        
        pos = r*adjust + (1-r)*random.random()
        
        self.bst = round(min_val + ((max_val-min_val) * pos))
    
    def generate_name(self):
        parts_set = set()
        primary_parts_set = set()
        
        is_baby = False
        if Flags.THREE_STAGES in self.flags or Flags.TWO_STAGES in self.flags:
            is_baby = self.previous_stage == None
        
        for theme in self.themes:
            namestring_sets = []
            
            if 'namestrings' in themedata[theme]:
                namestring_sets.append(themedata[theme]['namestrings'])
            if is_baby and 'namestrings_baby' in themedata[theme]:
                namestring_sets.append(themedata[theme]['namestrings_baby'])
                
            for namestrings in namestring_sets:
                parts_set.update(namestrings)
                
                if 'primary' in themedata[theme] and themedata[theme]['primary']:
                    primary_list = list(namestrings)
                    random.shuffle(primary_list)
                    for part in primary_list[0:min(5, len(primary_list))]:
                        primary_parts_set.add(part)
        
        if is_baby:
            parts_set.update(generic_baby_namestrings)
            
            primary_babyparts = list(generic_baby_namestrings)
            random.shuffle(primary_babyparts)
            primary_parts_set.update(primary_babyparts[0:min(3, len(primary_babyparts))])
        
        if len(primary_parts_set) == 0:
            primary_parts_set = parts_set
        
        #print(('!BABY!' if is_baby else ''), primary_parts_set)
        
        #speculative! TODO figure out if good or not
        selected_parts = set()
        primary_parts_set = list(primary_parts_set)
        parts_set = list(parts_set)
        
        for i in range(0,100):
            selected_parts.add(random.choice(primary_parts_set))
            if len(selected_parts) >= 25:
                break
        
        target_len = len(selected_parts) + 5
        for i in range(0,100):
            selected_parts.add(random.choice(parts_set))
            if len(selected_parts) >= target_len:
                break
        
        #print(len(selected_parts), selected_parts)
        
        self.name = None
        for i in range(1,100):
            #if random.random() > 0.66: TODO speculative
            #    parts = list(primary_parts_set)
            #else:
            #    parts = list(parts_set)
            parts = list(selected_parts)
            random.shuffle(parts)
            start = start_word = parts.pop()
            
            self.name = start # worst case scenario: the name is just this
            
            forbidden_words = set()
            for theme in self.themes:
                if theme in self.initial_themes:
                    continue
                if 'namestrings' in themedata[theme] and start_word in themedata[theme]['namestrings']:
                    forbidden_words.update(themedata[theme]['namestrings'])
                if 'namestrings_baby' in themedata[theme] and start_word in themedata[theme]['namestrings_baby']:
                    forbidden_words.update(themedata[theme]['namestrings_baby'])
            
            if start_word in generic_baby_namestrings:
                forbidden_words.update(generic_baby_namestrings)
            
            start = start[0:min(len(start), random.randint(3, 7))]
            last_letter = start[-1]
            
            end = end_word = ''
            for part in parts:
                if part in forbidden_words:
                    continue
                if last_letter in part:
                    end_word = part
                    index = part.index(last_letter)+1
                    end = part[index:min(len(part), index + random.randint(3,7))]
                    
                    if len(end) < 3 or start + end == start or start + end == end:
                        continue
                    
                    break
            
            if end == '':
                continue
            
            self.name = start + end
            
            if len(self.name) > 10:
                continue
            
            if self.name in ALL_NAMESTRINGS:
                continue
            
            if MORE_THAN_3_SUCC_SAME_CHARS.search(self.name) != None:
                continue
            
            if MORE_THAN_4_SUCC_VOWELS.search(self.name) != None or MORE_THAN_4_SUCC_CONSONANTS.search(self.name) != None:
                continue
            
            if MORE_THAN_3_END_VOWELS.search(self.name) != None or MORE_THAN_3_END_CONSONANTS.search(self.name) != None:
                continue
            
            if self.name[0:5] in PREVIOUS_NAME_STARTS:
                continue
            
            if self.name in parts:
                continue
            
            if len(end) <= 1 and (not start_word in self.name) and (not end_word in self.name):
            
                continue
            
            PREVIOUS_NAME_STARTS.add(self.name[0:5])
            
            break
        
        self.name = self.name.upper()
        self.name_start = start_word
        self.name_end = end_word
    
    def generate_type(self):
        necessary_types = set()
        possible_types = set()
        
        for theme in self.themes:
            data = themedata[theme]
            
            if 'necessary_types' in data:
                necessary_types.update(data['necessary_types'])
            
            if 'possible_types' in data:
                possible_types.update(data['possible_types'])
        
        necessary_types = list(necessary_types)
        possible_types = list(possible_types)
        self.types = []
        
        if len(necessary_types) == 0 and len(possible_types) == 0:
            self.types.append('NORMAL')
        elif len(necessary_types) == 0:
            self.types.append(take_random(possible_types))
            
            if len(possible_types) != 0:
                self.types.append(take_random(possible_types))
        else:
            self.types.append(take_random(necessary_types))
            
            if len(necessary_types) != 0:
                self.types.append(take_random(necessary_types))
            
            if len(self.types) == 1 and len(possible_types) != 0 and random.random() > 0.5:
                self.types.append(take_random(possible_types))
        
        # duplicate single type
        if len(self.types) == 1:
            self.types = [ self.types[0], self.types[0] ]
        
        # make flying second type always
        if self.types[0] == 'FLYING':
            self.types = [ self.types[1], self.types[0] ]
        
        # adjust starters
        if Flags.GRASS_STARTER in self.flags and self.types[0] != 'GRASS':
            if self.types[1] == 'GRASS':
                self.types = [self.types[1], self.types[0]]
            else:
                self.types = ['GRASS', self.types[0]]
        
        if Flags.FIRE_STARTER in self.flags and self.types[0] != 'FIRE':
            if self.types[1] == 'FIRE':
                self.types = [self.types[1], self.types[0]]
            else:
                self.types = ['FIRE', self.types[0]]
        
        if Flags.WATER_STARTER in self.flags and self.types[0] != 'WATER':
            if self.types[1] == 'WATER':
                self.types = [self.types[1], self.types[0]]
            else:
                self.types = ['WATER', self.types[0]]
        
    def generate_abilities(self):
        possible_abilities = set()
        
        for theme in self.themes:
            if 'abilities' in themedata[theme]:
                possible_abilities.update(themedata[theme]['abilities'])
        
        possible_abilities = list(possible_abilities)
        
        if random.random() > 0.5 and len(possible_abilities) >= 2:
            self.abilities = [ take_random(possible_abilities), take_random(possible_abilities) ]
        else:
            self.abilities = [ take_random(possible_abilities), 'NONE' ]
        
        if 'LEVITATE' in self.abilities:
            self.abilities = [ 'LEVITATE', 'NONE' ]
        
        if Flags.GRASS_STARTER in self.flags:
            self.abilities = [ 'OVERGROW', 'NONE' ]
        
        if Flags.WATER_STARTER in self.flags:
            self.abilities = [ 'TORRENT', 'NONE' ]
        
        if Flags.FIRE_STARTER in self.flags:
            self.abilities = [ 'BLAZE', 'NONE' ]
    
    def generate_moves(self):
        moves = set()
        
        for theme in self.themes:
            if 'moves' in themedata[theme]:
                moves.update(themedata[theme]['moves'])
        
        self.moves = moves
    
    def generate_egg_groups(self):
        egg_groups = set()
        
        for theme in self.themes:
            if 'egg_groups' in themedata[theme]:
                egg_groups.update(themedata[theme]['egg_groups'])
        
        egg_groups = list(egg_groups)
        random.shuffle(egg_groups)
        
        self.egg_groups = []
        
        while len(egg_groups) >= 1 and len(self.egg_groups) < 2:
            self.egg_groups.append(egg_groups.pop())
        
        if len(self.egg_groups) == 1:
            self.egg_groups.append(self.egg_groups[0])
        
        if Flags.LEGENDARY in self.flags or Flags.LEGENDARY_TRIO in self.flags or Flags.MYTHICAL in self.flags:
            self.egg_groups = ['UNDISCOVERED', 'UNDISCOVERED']
        
        if Flags.DITTO in self.flags:
            self.egg_groups = ['DITTO', 'DITTO']
    
    def calc_max_non_stab_perc(self, type_string):
        val = 0.8
        if type_string == 'BUG':
            val = 0.9
        if type_string == 'DARK':
            val = 0.9
        if type_string == 'DRAGON':
            val = 0.9
        if type_string == 'STEEL':
            val = 0.9
        return val
    
    
    def pick_move(self, moves, picked, target_len):
        moves = list(moves)
        for already_picked in picked:
            moves.remove(already_picked)
        try_move = None
        
        too_much_damage = False
        too_much_status = False
        stab_1_wanted = False
        stab_2_wanted = False
        weak_attack_wanted = False
        
        MAX_NON_STAB_1_PERC = self.calc_max_non_stab_perc(self.types[0])
        MAX_NON_STAB_2_PERC = self.calc_max_non_stab_perc(self.types[1])
        
        for i in range(0, 50):
            random.shuffle(moves)
            
            if too_much_damage and too_much_status:
                too_much_status = False
            
            if stab_1_wanted and stab_2_wanted:
                stab_2_wanted = False
                stab_1_wanted = True
                too_much_status = False
            
            for try_this in moves:
                try_move = try_this
                if too_much_damage and (move_data[try_move].damaging):
                    continue
                if too_much_status and (not move_data[try_move].damaging):
                    continue
                if stab_1_wanted and (((move_data[try_move].type != self.types[0]) or not move_data[try_move].damaging)):
                    continue
                if stab_2_wanted and (((move_data[try_move].type != self.types[1]) or not move_data[try_move].damaging)):
                    continue
                if weak_attack_wanted and (not (move_data[try_move].damaging and move_data[try_move].power < 50)):
                    continue
                
                reject_similar = False
                for similar_set in similar_move_sets:
                    if try_move in similar_set:
                        for similar in similar_set:
                            if similar in picked:
                                reject_similar = True
                
                if reject_similar:
                    continue
                
                break
            
            new_picked = set(picked)
            new_picked.add(try_move)
            
            too_much_damage = too_much_status = stab_1_wanted = stab_2_wanted = weak_attack_wanted = False
            
            # avoid: more than 80 % damaging
            damaging = 0
            for pick in new_picked:
                if move_data[pick].damaging:
                    damaging = damaging + 1
            
            if (move_data[try_move].damaging) and damaging > target_len*0.8:
                too_much_damage = True
            
            # avoid: more than 60 % non-damaging
            non_damaging = 0
            for pick in new_picked:
                if not move_data[pick].damaging:
                    non_damaging = non_damaging + 1
            
            if (not move_data[try_move].damaging) and non_damaging > target_len*0.6:
                too_much_status = True
            
            # avoid: more than MAX_NON_STAB_PERC % non-stab
            non_stab_1 = 0
            for pick in new_picked:
                pick_type = move_data[pick].type
                if pick_type != self.types[0] or (not move_data[pick].damaging):
                    non_stab_1 = non_stab_1+1
            
            if (move_data[try_move].type != self.types[0]) and non_stab_1 > target_len*MAX_NON_STAB_1_PERC:
                stab_1_wanted = True
            
            non_stab_2 = 0
            for pick in new_picked:
                pick_type = move_data[pick].type
                if pick_type != self.types[1] or (not move_data[pick].damaging):
                    non_stab_2 = non_stab_2+1
            
            if (move_data[try_move].type != self.types[1]) and non_stab_2 > target_len*MAX_NON_STAB_2_PERC:
                stab_2_wanted = True
            
            # at least 2 attacks with less than 60 power
            weak_attacks = 0
            for pick in new_picked:
                if move_data[pick].damaging and move_data[pick].power < 50:
                    weak_attacks = weak_attacks + 1
            
            if (not (move_data[try_move].damaging and move_data[try_move].power < 50)) and weak_attacks < 2:
                weak_attack_wanted = True
            
            if too_much_damage or too_much_status or stab_1_wanted or stab_2_wanted or weak_attack_wanted:
                continue
            
            return try_move
        
        return try_move
    
    def generate_learnset(self):
        learnset = set()
        target_len = random.randint(8, 12)
        movelist = list(self.moves)
        
        if Flags.DITTO in self.flags:
            self.learnset = [(1, move_data['TRANSFORM'])]
            return
        
        # give starters good starting move
        if Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags:
            target_len = random.randint(10, 12)
            
            if 'SCRATCH' in movelist:
                learnset.add('SCRATCH')
            elif 'POUND' in movelist:
                learnset.add('POUND')
            else:
                learnset.add('TACKLE')
                if 'TACKLE' not in movelist:
                    movelist.append('TACKLE')
                    self.moves.add('TACKLE')
        
        tries = 0
        while len(learnset) < target_len and tries < 1000:
            learnset.add(self.pick_move(movelist, learnset, target_len))
            tries = tries + 1
        
        learnset = list(learnset)
        for i in range(0, len(learnset)):
            learnset[i] = move_data[learnset[i]]
        
        learnset = sort_move_list(learnset)
        
        if not learnset[0].damaging:
            if learnset[1].damaging:
                learnset[0], learnset[1] = learnset[1], learnset[0]
            elif learnset[2].damaging:
                learnset[0], learnset[2] = learnset[2], learnset[0]
            elif learnset[3].damaging:
                learnset[0], learnset[3] = learnset[3], learnset[0]
        
        # avoid two damaging moves of same type in a row
        for i in range(0, len(learnset)-2):
            mvs = learnset[i:i+3]
            if mvs[0].damaging and mvs[1].damaging and mvs[0].type == mvs[1].type and (not mvs[2].damaging):
                learnset[i+1], learnset[i+2] = learnset[i+2], learnset[i+1]
            elif mvs[1].damaging and mvs[2].damaging and mvs[1].type == mvs[2].type and (not mvs[0].damaging):
                learnset[i], learnset[i+1] = learnset[i+1], learnset[i]
        
        # avoid too many dmg/status in a row
        for i in range(0, len(learnset)-3):
            mvs = learnset[i:i+4]
            dmg_cat = mvs[0].damaging
            can_fix = (mvs[1].damaging == dmg_cat) and (mvs[2].damaging == dmg_cat) and (mvs[3].damaging != dmg_cat)
            if can_fix:
                learnset[i+2], learnset[i+3] = learnset[i+3], learnset[i+2]
        
        # transform list into tuples (level, move)
        if Flags.SINGLE in self.flags:
            if Flags.LEGENDARY in self.flags or Flags.MYTHICAL in self.flags or Flags.LEGENDARY_TRIO in self.flags:
                target_max_lvl = random.randint(70, 90)
            else:
                target_max_lvl = random.randint(40, 60)
                
        elif Flags.TWO_STAGES in self.flags: # bst 250–450
            lo = 45
            hi = 65
            d = (self.bst-250)/200
            target_max_lvl = int(hi*d + lo*(1-d))
            
        elif Flags.THREE_STAGES in self.flags: # bst 200–350
            lo = 40
            hi = 50
            d = (self.bst-200)/150
            target_max_lvl = int(hi*d + lo*(1-d))
        
        lvl_1_moves = random.randint(1,3)
        if len(learnset) < 10:
            lvl_1_moves = max(1, lvl_1_moves-1)
        
        if Flags.GRASS_STARTER in self.flags or Flags.WATER_STARTER in self.flags or Flags.FIRE_STARTER in self.flags:
            lvl_1_moves = 2
        
        delta = int(target_max_lvl / (len(learnset) - lvl_1_moves))
        
        for i in range(0, lvl_1_moves):
            learnset[i] = (1, learnset[i])
        
        acc = 1 + delta
        for i in range(lvl_1_moves, len(learnset)):
            learnset[i] = (acc, learnset[i])
            acc = acc + delta
        
        self.learnset = learnset
    
    def evo_adjust_learnset_levels(self):
        if isinstance(self.previous_stage.evo_type, LevelEvo):
            acc = 2
            for i in range(0, len(self.learnset)):
                if self.learnset[i][0] > self.previous_stage.evo_type.level:
                    self.learnset[i] = (self.learnset[i][0]+acc, self.learnset[i][1])
                    acc = acc + 2
        
        # for some fully-evolved pokemon, add extra moves at level 1
        if Flags.LAST_EVOLVABLE_STAGE in self.previous_stage.flags and random.random() > 0.5:
            possible_moves = set()
            
            for mv in self.moves:
                if move_data[mv].value >= 120:
                    possible_moves.add(move_data[mv])
            
            for (lvl, mv) in self.learnset:
                if mv in possible_moves:
                    possible_moves.remove(mv)
            
            for tm in tm_list:
                if move_data[tm] in possible_moves:
                    possible_moves.remove(move_data[tm])
            
            if len(possible_moves) != 0:
                extra_move = random.choice(list(possible_moves))
                new_ls = [(1, extra_move)]
                new_ls.extend(self.learnset)
                self.learnset = new_ls
    
    def assign_base_stats(self):
        if self.stat_spread_weights == None:
            mk = stat_spread_weight
            self.stat_spread_weights = [ mk(), mk(), mk(), mk(), mk(), mk() ]
            
            d = 0.2 + random.random() * 0.6
            for i in range(0,6):
                type_weight = (type_bst_spreads[self.types[0]][i] + type_bst_spreads[self.types[1]][i]) / 2
                
                for theme in self.themes:
                    if 'stat_adjustment' in themedata[theme]:
                        type_weight = type_weight + themedata[theme]['stat_adjustment'][i]
                
                self.stat_spread_weights[i] = round((1-d)*self.stat_spread_weights[i] + d*type_weight)
        
        else:
            for i in range(0,6):
                self.stat_spread_weights[i] = self.stat_spread_weights[i] + random.randint(-5,5)
            
        total_weight = sum(self.stat_spread_weights)
        
        self.stats = [0, 0, 0, 0, 0, 0]
        
        for i in range(0,6):
            self.stats[i] = round((self.bst) * (self.stat_spread_weights[i]/total_weight))
        
    def generate_defeat_yield(self):
        if Flags.LEGENDARY in self.flags or Flags.MYTHICAL in self.flags or Flags.LEGENDARY_TRIO in self.flags:
            evs = 3
            exp_range = (212, 220)
            bst_range = (580, 680)
        elif Flags.SINGLE in self.flags: # unevolving
            exp_range = (98, 219)
            bst_range = (350, 550)
            evs = 2
        elif self.previous_stage == None: # stage 1
            exp_range = (39, 137)
            bst_range = (200, 450)
            evs = 1
        elif self.previous_stage.previous_stage == None: # stage 2
            exp_range = (113, 212)
            bst_range = (300, 600)
            evs = 2
        else: # stage 3
            exp_range = (160, 218)
            bst_range = (400, 600)
            evs = 3
        
        d = (self.bst - bst_range[0])/(bst_range[1] - bst_range[0])
        self.exp_yield = round(d*exp_range[1] + (1-d)*exp_range[0])
        
        if self.previous_stage != None:
            if self.previous_stage.exp_yield > self.exp_yield:
                raise "fuckin' yikes"
        
        top_stat = -1
        top_stat_val = -1
        top_stat2 = -1
        top_stat2_val = -1
        
        self.ev_yield = [0] * len(self.stats)
        
        for i in range(0, len(self.stats)):
            if self.stats[i] > top_stat_val:
                top_stat = i
                top_stat_val = self.stats[i]
        
        for i in range(0, len(self.stats)):
            if i != top_stat and self.stats[i] > top_stat2_val:
                top_stat2 = i
                top_stat2_val = self.stats[i]
        
        if evs == 1:
            self.ev_yield[top_stat] = 1
        else:
            if top_stat_val - top_stat2_val > 15:
                self.ev_yield[top_stat] = evs
            else:
                self.ev_yield[top_stat] = evs-1
                self.ev_yield[top_stat2] = evs - self.ev_yield[top_stat]
    
    def generate_held_items(self):
        if self.previous_stage != None:
            self.held_items = self.previous_stage.held_items
        else:
            self.held_items = ['NONE', 'NONE']
        
        items = []
        for theme in self.themes:
            if 'held_items' in themedata[theme]:
                items.extend(themedata[theme]['held_items'])
        
        if random.random() > 0.75 and len(items) != 0:
            item1 = random.choice(items)
            item2 = random.choice(items)
            
            if self.held_items[0] != 'NONE' or self.held_items[1] != 'NONE':
                if self.held_items[0] == 'NONE':
                    self.held_items[0] = item1
                if self.held_items[1] == 'NONE':
                    self.held_items[1] = item1
            else:          
                if random.random() > 0.9:
                    self.held_items = [item1, item1]
                elif random.random() > 0.9:
                    self.held_items = [item1, item2]
                elif random.random() > 0.75:
                    self.held_items = [item1, 'NONE']
                else:
                    self.held_items = ['NONE', item1]
    
    def generate_gender_ratio(self):
        self.gender_ratio = 'PERCENT_FEMALE(50)'
        
        if ('AMORPHOUS' in self.egg_groups or 'MINERAL' in self.egg_groups) and random.random() > 0.9:
            self.gender_ratio = 'MON_GENDERLESS'
        
        if Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags or Flags.GRASS_STARTER in self.flags or Flags.FOSSIL in self.flags:
            self.gender_ratio = 'PERCENT_FEMALE(12.5)'
        
        if Flags.DITTO in self.flags:
            self.gender_ratio = 'MON_GENDERLESS'
        
        if 'UNDISCOVERED' in self.egg_groups:
            self.gender_ratio = 'MON_GENDERLESS'
    
    def generate_egg_cycles(self):
        if 'UNDISCOVERED' in self.egg_groups:
            self.egg_cycles = 120
            return
        
        base = self
        while base.previous_stage != None:
            base = base.previous_stage
        
        #cycles_range = (3, 8)
        #bst_range = (200, 450)
        d = (self.bst-200)/250
        self.egg_cycles = int(8*d + 3*(1-d))
        if self.egg_cycles > 8:
            self.egg_cycles = 8
        if self.egg_cycles < 3:
            self.egg_cycles = 3
        self.egg_cycles = self.egg_cycles * 5
    
    def generate_base_friendship(self):
        self.base_friendship = 70
        
        if 'cute' in self.themes and random.random() > 0.75:
            if random.random() > 0.5:
                self.base_friendship = 140
            else:
                self.base_friendship = 100
        
        if ('evil' in self.themes or 'ghost' in self.themes or 'blob' in self.themes or 'angry' in self.themes) and random.random() > 0.75:
            self.base_friendship = 35
        
        if Flags.LEGENDARY_TRIO in self.flags:
            self.base_friendship = 35
        if Flags.LEGENDARY in self.flags or Flags.MYTHICAL in self.flags:
            self.base_friendship = 0
    
    def generate_growth_rate(self):
        self.growth_rate = 'MEDIUM_FAST'
        
        if Flags.PSEUDO in self.flags or Flags.LEGENDARY in self.flags or Flags.LEGENDARY_TRIO in self.flags:
            self.growth_rate = 'SLOW'
            return
        
        if Flags.WATER_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.GRASS_STARTER in self.flags:
            self.growth_rate = 'MEDIUM_SLOW'
            return
        
        if random.random() < 0.3:
            self.growth_rate = 'MEDIUM_SLOW'
            return
        
        if random.random() < 0.2:
            self.growth_rate = 'FAST'
            return
        
        if random.random() < 0.1:
            self.growth_rate = 'SLOW'
            return
        
        if random.random() < 0.05:
            if random.random() > 0.5:
                self.growth_rate = 'ERRATIC'
            else:
                self.growth_rate = 'FLUCTUATING'
    
    def generate_flee_rate(self):
        self.flee_rate = 25
        
        if self.bst > 250:
            self.flee_rate = 50
        
        if self.bst > 350 or self.stats[5] > 70:
            self.flee_rate = 75
        
        if self.bst > 400 or self.stats[5] > 90:
            self.flee_rate = 100
        
        if self.bst > 450 or self.stats[5] > 110:
            self.flee_rate = 125
        
        if self.stats[5] < 40:
            self.flee_rate = 25
    
    def generate_tms(self):
        self.tms = set()
        self.tutor_moves = set()
        
        if Flags.DITTO in self.flags:
            return
        
        for tm in tm_list:
            if tm in universal_tms:
                self.tms.add(tm)
                continue
            
            if tm in self.moves:
                self.tms.add(tm)
                continue
            
            for theme in self.themes:
                if 'tms' in themedata[theme]:
                    if tm in themedata[theme]['tms']:
                        self.tms.add(tm)
        
        for move in tutor_move_list:
            if move in universal_tms:
                self.tutor_moves.add(move)
            
            if move in self.moves:
                self.tutor_moves.add(move)    
            
            for theme in self.themes:
                if 'tms' in themedata[theme]:
                    if move in themedata[theme]['tms']:
                        self.tutor_moves.add(move)   
    
    def generate_egg_moves(self):
        self.egg_moves = set()
        
        if 'UNDISCOVERED' in self.egg_groups or Flags.DITTO in self.flags:
            return
        
        target_amount = random.randint(3,8)
        tries = 0
        choices = list(self.moves)
        
        not_good = set()
        for lrn in self.learnset:
           not_good.add(lrn[1].name)
        
        while tries < 100 and len(self.egg_moves) < target_amount:
           move = random.choice(choices)
           if not move in not_good:
               self.egg_moves.add(move)
           tries = tries + 1
    
    def generate_image_colors(self):
        choices = set()
        choices.update(tuple(l) for l in type_colors[self.types[0]])
        choices.update(tuple(l) for l in type_colors[self.types[1]])
        choices = list(choices)
        
        self.image_colors = [generate_color(choices), generate_color(choices)]
        
        while abs(self.image_colors[0][0] - self.image_colors[1][0]) < 40 and abs(self.image_colors[0][1] - self.image_colors[1][1]) < 40 and abs(self.image_colors[0][2] - self.image_colors[1][2]) < 40:
            self.image_colors[1] = generate_color(choices, distort=True)
        
        # determine pokedex body color by taking main color
        avg_color = self.image_colors[0]
        
        chosen = None
        last_d = 999999999
        for dex_color in DEX_COLORS.keys():
            rgb = DEX_COLORS[dex_color]
            #d = ((rgb[0]-avg_color[0])*0.30)**2 + ((rgb[1]-avg_color[1])*0.59)**2 + ((rgb[2]-avg_color[2])*0.11)**2
            d = ((rgb[0]-avg_color[0]))**2 + ((rgb[1]-avg_color[1]))**2 + ((rgb[2]-avg_color[2]))**2
            if d < last_d:
                last_d = d
                chosen = dex_color
        
        self.body_color = chosen

    def generate_dex_data(self):
        
        # determine dex category
        choices = set()
        backup_choices = set()
        for theme in self.themes:
            if 'primary' in themedata[theme] and themedata[theme]['primary']:
                choices.update(themedata[theme]['namestrings'])
            elif 'namestrings' in themedata[theme]:
                backup_choices.update(themedata[theme]['namestrings'])
        
        if len(choices) == 0:
            choices = backup_choices
        
        choices = list(choices)
        self.category = random.choice(choices).upper()
        while len(self.category) > 10:
            self.category = random.choice(choices).upper()
        
        if self.previous_stage != None and random.random() > 0.5:
            self.category = self.previous_stage.category
        
        # determine weight
        avg_w = (average_weights[self.types[0]] + average_weights[self.types[1]])/2
        w = -1
        while w < 1:
            w = nprandom.normal(loc=avg_w, scale=avg_w)
        if w > 99999:
            w = 99999
        
        self.weight = int(w)
        
        ws = []
        ws.append(self.weight)
        if self.previous_stage != None:
            ws.append(self.previous_stage.weight)
            if self.previous_stage.previous_stage != None:
                ws.append(self.previous_stage.previous_stage.weight)
        
        ws.sort()
        
        if len(ws) == 2:
            self.previous_stage.weight = ws[0]
            self.weight = ws[1]
        elif len(ws) == 3:
            self.previous_stage.previous_stage.weight = ws[0]
            self.previous_stage.weight = ws[1]
            self.weight = ws[2]
        
        # determine height
        avg_h = (average_heights[self.types[0]] + average_heights[self.types[1]])/2
        h = -1
        while h < 1:
            h = nprandom.normal(loc=avg_h, scale=avg_h/2)
        if h > 200:
            h = 200
        
        self.height = int(h)
        
        hs = []
        hs.append(self.height)
        if self.previous_stage != None:
            hs.append(self.previous_stage.height)
            if self.previous_stage.previous_stage != None:
                hs.append(self.previous_stage.previous_stage.height)
        
        hs.sort()
        
        if len(hs) == 2:
            self.previous_stage.height = hs[0]
            self.height = hs[1]
        elif len(hs) == 3:
            self.previous_stage.previous_stage.height = hs[0]
            self.previous_stage.height = hs[1]
            self.height = hs[2]

DEX_COLORS = {
    'RED'    : [ 240, 88,  104 ],
    'BLUE'   : [ 48,  136, 240 ],
    'YELLOW' : [ 240, 208, 72  ],
    'GREEN'  : [ 64,  184, 104 ],
    'BLACK'  : [ 88,  88,  88  ],
    'BROWN'  : [ 176, 112, 48  ],
    'PURPLE' : [ 168, 104, 192 ],
    'GRAY'   : [ 160, 160, 160 ],
    'WHITE'  : [ 240, 240, 240 ],
    'PINK'   : [ 248, 144, 200 ]
}        

def generate_color(choices, distort=False):
    c1 = random.choice(choices)
    c2 = random.choice(choices)
    
    while c1 == c2:
        c2 = random.choice(choices)
    
    r = random.random()
    cr = 1 - r
    
    if distort:
        if random.random() > 0.5:
            c3 = (0, 0, 0)
        else:
            c3 = (255, 255, 255)
        
        p = random.random()
        cp = 1-p
        
        c2 = (int(p*c3[0] + cp*c2[0]), int(p*c3[1] + cp*c2[1]), int(p*c3[2] + cp*c2[2]))
    
    return [int(r*c1[0] + cr*c2[0]), int(r*c1[1] + cr*c2[1]), int(r*c1[2] + cr*c2[2])]

def stat_spread_weight():
    if random.random() > 0.5:
        return random.randint(70, 100)
    if random.random() > 0.75:
        return random.randint(50, 130)
    return random.randint(30, 180)

def weighted_pick_theme(possibilities, normalize_untyped_ratio=False):
    result_types = defaultdict(lambda: [])
    typed_themes = []
    untyped_themes = []
    
    for theme in possibilities:
        if 'necessary_types' in themedata[theme] or 'possible_types' in themedata[theme]:
            typed_themes.append(theme)
        else:
            untyped_themes.append(theme)
        
        if 'necessary_types' in themedata[theme]:
            result_types[theme].extend(themedata[theme]['necessary_types'])
        if 'possible_types' in themedata[theme]:
            result_types[theme].extend(themedata[theme]['possible_types'])
    
    
    untyped_chance = len(untyped_themes) / (len(untyped_themes) + len(typed_themes))
    
    if normalize_untyped_ratio and len(untyped_themes) != 0:
        untyped_chance = 0.35
    
    if random.random() < untyped_chance:
        return random.choice(untyped_themes)
    else:
        weights = []
        for theme in typed_themes:
            acc = 0
            for tp in result_types[theme]:
                acc = acc + type_weights[tp]
            acc = acc / len(result_types[theme])
            weights.append(acc)
        
        return random.choices(typed_themes, weights)[0]

used_combos = defaultdict(lambda: 0)
total_combos = defaultdict(lambda: 0)

def make_pkmn(slot, flags, bst_range=(0,0), reroll=True):
    pkmn = Pokemon(bst_range=bst_range, flags=flags)
    
    archetype = weighted_pick_theme(archetypes)
    subarchetype = weighted_pick_theme(subarchetypes, normalize_untyped_ratio=True)
    
    if Flags.WATER_STARTER in flags:
        archetype = random.choice(['water_animal', 'small_animal', 'dark_animal',  'ground_animal', 'monster', 'humanoid_fighter', 'humanoid_psychic', 'bird'])
        subarchetype = 'water_elemental'
    if Flags.FIRE_STARTER in flags:
        archetype = random.choice(['small_animal', 'dark_animal', 'ground_animal', 'monster', 'humanoid_fighter', 'humanoid_psychic', 'bird'])
        subarchetype = 'fire_elemental'
    if Flags.GRASS_STARTER in flags:
        archetype = random.choice(['plant', 'small_animal', 'dark_animal', 'ground_animal', 'monster', 'humanoid_fighter', 'humanoid_psychic', 'bird'])
        subarchetype = 'grass_elemental'
    
    if Flags.FOSSIL in flags:
        subarchetype = 'rocky'
    
    if Flags.DITTO in flags:
        archetype = 'blob'
    
    if Flags.LEGENDARY_TRIO in flags or Flags.MYTHICAL in flags or Flags.LEGENDARY in flags:
        if len(special_dex_slots[slot]) == 3:
            archetype = special_dex_slots[slot][2]
    
    pkmn.themes.add(archetype)
    pkmn.themes.add(subarchetype)
    
    pkmn.generate()
    
    type_combo = tuple(sorted(pkmn.types))
    
    if reroll:
        if (type_combo[0] != type_combo[1]) and used_combos[type_combo] > 2:
            # print('rerolling (used combo)', type_combo)
            for i in range(0,20):
                pkmn = make_pkmn(slot, flags, bst_range=bst_range, reroll=False)
                type_combo = tuple(sorted(pkmn.types))
                if not (type_combo[0] != type_combo[1]) and used_combos[type_combo] > 2:
                    break
            # print('got', type_combo)  
        
        if total_combos[type_combo[0]] >= 6 and total_combos[type_combo[1]] >= 6:
            # print('rerolling (common types)', type_combo)
            for i in range(0,20):
                pkmn = make_pkmn(slot, flags, bst_range=bst_range, reroll=False)
                type_combo = tuple(sorted(pkmn.types))
                if not (total_combos[type_combo[0]] >= 6 and total_combos[type_combo[1]] >= 6):
                    break
            # print('got', type_combo)  
        
        if total_combos[type_combo[0]] >= 10 or total_combos[type_combo[1]] >= 10:
            # print('rerolling (common type)', type_combo[0])
            for i in range(0,20):
                pkmn = make_pkmn(slot, flags, bst_range=bst_range, reroll=False)
                type_combo = tuple(sorted(pkmn.types))
                if not (total_combos[type_combo[0]] >= 10 or total_combos[type_combo[1]] >= 10):
                    break
            # print('got', type_combo)
        
    if reroll:
        used_combos[type_combo] = used_combos[type_combo] + 1
        
        total_combos[type_combo[0]] = total_combos[type_combo[0]] + 1
        if type_combo[0] != type_combo[1]:
            total_combos[type_combo[1]] = total_combos[type_combo[1]] + 1
        
    return pkmn

def debug_type_distribution():
    types = defaultdict(lambda: 0)
    for i in range(0,10000):
        pkmn = make_pkmn()
        types[pkmn.types[0]] = types[pkmn.types[0]] + 1
        types[pkmn.types[1]] = types[pkmn.types[0]] + 1
    
    #maxval = max(types.values())
    
    #for k in types.keys():
    #    types[k] = int(types[k])/maxval*100
    
    pprint.pp(types)

ungainable_types = [ 'NORMAL', 'FLYING', 'BUG' ]

# no evo: 350–500
# stage 1 of 3: 200–350 // + 100–125 per evo
# stage 1 of 2: 250–450 // + 100–150
def generate_family(slot, evo_cat, special=None):
    flags = set([evo_cat])
    
    if special != None:
        flags.add(special)
        
    if evo_cat == Flags.SINGLE:
        bst_range = (350, 550)
        
        if special == Flags.LEGENDARY:
            bst_range = (680, 680)
        if special == Flags.MYTHICAL:
            bst_range = (600, 600)
        if special == Flags.LEGENDARY_TRIO:
            bst_range = (580, 580)
        
        pkmn = make_pkmn(slot, flags, bst_range=bst_range)
        
        if not special == Flags.DITTO:
            pkmn.tms.add('HYPER_BEAM')
        return [ pkmn ]
        
    elif evo_cat == Flags.TWO_STAGES:
        flags.add(Flags.LAST_EVOLVABLE_STAGE)
        pkmn = make_pkmn(slot, flags, bst_range=(250, 450))
        pkmn2 = pkmn.evolve(bst_increase=random.randint(100, 150))
        
        if random.random() > 0.5 and not pkmn.types[1] in ungainable_types:
            pkmn.types[1] = pkmn.types[0]
        
        pkmn2.tms.add('HYPER_BEAM')
        return [ pkmn, pkmn2 ]
        
    elif evo_cat == Flags.THREE_STAGES:
        bst_range = (200, 350)
        bst_increase_1 = random.randint(100, 125)
        bst_increase_2 = random.randint(100, 125)
        
        if special == Flags.FIRE_STARTER or special == Flags.GRASS_STARTER or special == Flags.WATER_STARTER:
            bst_range = (309, 318)
            bst_increase_1 = random.randint(87, 96)
            bst_increase_2 = random.randint(116, 134)
        
        if special == Flags.PSEUDO:
            bst_range = (300, 300)
            bst_increase_1 = 120
            bst_increase_2 = 180
        
        pkmn = make_pkmn(slot, flags, bst_range=bst_range)
        pkmn2 = pkmn.evolve(bst_increase=bst_increase_1)
        pkmn3 = pkmn2.evolve(bst_increase=bst_increase_2)
        
        if random.random() > 0.5 and not pkmn.types[1] in ungainable_types:
            pkmn.types[1] = pkmn.types[0]
            pkmn2.types[1] = pkmn2.types[0]
        
        pkmn3.tms.add('HYPER_BEAM')
        return [ pkmn, pkmn2, pkmn3 ]

def debug_gen_pkmn():
    pkmn = make_pkmn()
    print(pkmn.themes)
    print('type:', pkmn.types)
    print('abilities:', pkmn.abilities)
    print('egg groups:', pkmn.egg_groups)
    print(pkmn.learnset)

special_dex_slots = [None] * 152
special_dex_slots[1] = (Flags.THREE_STAGES, Flags.GRASS_STARTER)
special_dex_slots[4] = (Flags.THREE_STAGES, Flags.FIRE_STARTER)
special_dex_slots[7] = (Flags.THREE_STAGES, Flags.WATER_STARTER)

special_dex_slots[132] = (Flags.SINGLE, Flags.DITTO) # ditto

special_dex_slots[138] = (Flags.TWO_STAGES, Flags.FOSSIL) # fossil line 1
special_dex_slots[140] = (Flags.TWO_STAGES, Flags.FOSSIL) # fossil line 2
special_dex_slots[142] = (Flags.SINGLE, Flags.FOSSIL) # aerodactyl
special_dex_slots[143] = (Flags.SINGLE, None) # snorlax

legendary_birds_arch = random.choice(archetypes) # legendary birds
special_dex_slots[144] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)
special_dex_slots[145] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)
special_dex_slots[146] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)

special_dex_slots[147] = (Flags.THREE_STAGES, Flags.PSEUDO) # pseudo

mews_arch = random.choice(archetypes)
special_dex_slots[150] = (Flags.SINGLE, Flags.LEGENDARY, mews_arch) # mewtwo
special_dex_slots[151] = (Flags.SINGLE, Flags.MYTHICAL, mews_arch) # mew

def dex_sort_key(pk):
    # retrieve first form
    first = pk
    while first.previous_stage != None:
        first = first.previous_stage
    
    # retrieve final form
    final = pk
    while final.evo_target != None:
        final = final.evo_target
    
    val = round((first.bst + final.bst)/60)
    
    for tp in set(final.types):
        if tp == 'DRAGON':
            val = val + 1
        if tp == 'STEEL':
            val = val + 1
        if tp == 'GHOST':
            val = val + 1
        if tp == 'ICE':
            val = val + 1
        if tp == 'BUG':
            val = val - 1
        if tp == 'FLYING':
            val = val - 1
        if tp == 'GRASS':
            val = val - 1
        if tp == 'GROUND':
            val = val - 1
    
    return val

def debug_gen_dex():
    dex = []
    dex.append(None)
    
    while len(dex) <= 151:
        index = len(dex)
        
        if special_dex_slots[index] == None:
            special = None
            if random.random() > 0.2: # was 0.3
                if random.random() > 0.7:
                    evo_cat = Flags.THREE_STAGES
                else:
                    evo_cat = Flags.TWO_STAGES
            else:
                evo_cat = Flags.SINGLE
        else:
            evo_cat = special_dex_slots[index][0]
            special = special_dex_slots[index][1]
        
        if evo_cat == Flags.THREE_STAGES and (special_dex_slots[index+1] != None or special_dex_slots[index+2] != None):
            evo_cat = Flags.TWO_STAGES
        if evo_cat == Flags.TWO_STAGES and special_dex_slots[index+1] != None:
            evo_cat = Flags.SINGLE
        
        pks = generate_family(index, evo_cat, special)
        dex.extend(pks)
    
    # approximately sort dex by bst
    sorting = list(dex[10:138])
    sorting.sort(key=lambda pk: dex_sort_key(pk))
    dex[10:138] = sorting
    
    string = []
    
    for i in range(1, len(dex)):
        poke = dex[i]
        string.append(f'{i}: {poke.name.ljust(15)}\t{str(poke.types).ljust(30)}\t{poke.abilities}\t({index_to_id[str(i)]})')
        string.append(f'\t{poke.name_start} + {poke.name_end}, {poke.themes}')
        string.append(f'\tstats: {poke.stats}, bst: {sum(poke.stats)}')
        string.append(f'\tcatch rate: {poke.catch_rate}, gender ratio: {poke.gender_ratio}, base friendship: {poke.base_friendship}, flee rate: {poke.flee_rate}')
        string.append(f'\tegg groups: {poke.egg_groups}, egg cycles: {poke.egg_cycles}, growth rate: {poke.growth_rate}')
        string.append(f'\texp yield: {poke.exp_yield}, ev yield: {poke.ev_yield}, held items: {poke.held_items}')
        string.append(f'\tbody color: {poke.body_color}, category: {poke.category}, weight: {poke.weight/10} kg, height: {poke.height/10} m')
        string.append(f'\ttms: {poke.tms}')
        string.append(f'\ttutor moves: {poke.tutor_moves}')
        if poke.egg_moves != None:
            string.append(f'\tegg moves: {poke.egg_moves}')
        #print(f'\tflags: {poke.flags}')
        if poke.evo_target != None:
            string.append(f'\tevolves into {poke.evo_target.name} with {poke.evo_type}'),
        for mv in poke.learnset:
            string.append(f'\t{mv[0]}\t{mv[1].name}')
    
    with open('dex.txt', 'w') as f:
        f.write('\n'.join(string))
    
    # debug print for type spread
    families = set()
    for poke in dex[1:]:
        final = poke
        while final.evo_target != None:
            final = final.evo_target
        
        if Flags.LEGENDARY in final.flags:
            pass
        elif Flags.LEGENDARY_TRIO in final.flags:
            pass
        elif Flags.MYTHICAL in final.flags:
            pass
        else:
            families.add(final)
    
    combo_spread = defaultdict(lambda: 0)
    type_spread = defaultdict(lambda: 0)
    
    for fam in families:
        tp = tuple(sorted(fam.types))
        combo_spread[tp] = combo_spread[tp]+1
        
        type_spread[tp[0]] = type_spread[tp[0]]+1
        
        if(tp[0] != tp[1]):
            type_spread[tp[1]] = type_spread[tp[1]]+1
    
    for tp in type_weights.keys():
        print(f'{tp}: {type_spread[tp]}')
        
        for combo in combo_spread.keys():
            if combo[0] != tp and combo[1] != tp:
                continue
            print(f'\t{combo_spread[combo]} {"*" if combo[0] == tp else combo[0]}/{"*" if combo[1] == tp else combo[1]}')
    
    print()
    rare_types = []
    for tp in type_weights.keys():
        if type_spread[tp] < 5:
            rare_types.append(f'{tp} ({type_spread[tp]})')
    print('rare types:', ', '.join(rare_types))
    
    return dex

index_to_id = {}

get_id = re.compile('SPECIES_(\S+)\s([0-9]+)')
with open(pokered_folder + '/include/constants/species.h') as f:
    species_h = f.read()
for line in species_h.split('\n'):
    m = get_id.search(line)
    if m != None:
        index_to_id[m.group(2)] = m.group(1)

def output_to_json(dex):

    poke_to_id = {}
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        poke_to_id[poke.name] = index_to_id[str(index)]
        
    out = {
        'base_stats.h' : {},
        'species_names.h' : [],
        'egg_moves.h' : {},
        'evolution.h' : {},
        'level_up_learnsets.h' : {},
        'tmhm_learnsets.h' : {},
        'tutor_learnsets.h' : {},
        'image_colors' : [],
        'encounter_data' : {},
        'moves' : {},
        'teachable_moves' : [],
        'pokedex_entries.h' : {}
    }
    
    ids_to_learnset_pointers = {}
    get_pointer = re.compile('\[SPECIES_(\S+)\]\s=\s(.+),')
    with open(pokered_folder + '/src/data/pokemon/level_up_learnset_pointers.h') as f:
        pointers_h = f.read()
        for line in pointers_h.split('\n'):
            m = get_pointer.search(line)
            if m != None:
                ids_to_learnset_pointers[m.group(1)] = m.group(2)
    
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        
        identifier = index_to_id[str(index)]
        
        # src/data/pokemon/base_stats.h data
        
        entry = {}
        
        entry['baseHP'] = poke.stats[0]
        entry['baseAttack'] = poke.stats[1]
        entry['baseDefense'] = poke.stats[2]
        entry['baseSpeed'] = poke.stats[5]
        entry['baseSpAttack'] = poke.stats[3]
        entry['baseSpDefense'] = poke.stats[4]
        entry['type1'] = poke.types[0]
        entry['type2'] = poke.types[1]
        entry['catchRate'] = poke.catch_rate
        entry['expYield'] = poke.exp_yield
        entry['evYield_HP'] = poke.ev_yield[0]
        entry['evYield_Attack'] = poke.ev_yield[1]
        entry['evYield_Defense'] = poke.ev_yield[2]
        entry['evYield_Speed'] = poke.ev_yield[5]
        entry['evYield_SpAttack'] = poke.ev_yield[3]
        entry['evYield_SpDefense'] = poke.ev_yield[4]
        entry['item1'] = poke.held_items[0]
        entry['item2'] = poke.held_items[1]
        entry['genderRatio'] = poke.gender_ratio
        entry['eggCycles'] = poke.egg_cycles
        entry['friendship'] = poke.base_friendship
        entry['growthRate'] = poke.growth_rate
        entry['eggGroup1'] = poke.egg_groups[0]
        entry['eggGroup2'] = poke.egg_groups[1]
        entry['abilities'] = poke.abilities
        entry['safariZoneFleeRate'] = poke.flee_rate
        entry['bodyColor'] = poke.body_color
        entry['noFlip'] = 'FALSE'
        entry['__learnset_pointer'] = ids_to_learnset_pointers[identifier]
        
        out['base_stats.h'][identifier] = entry
        
        # src/data/pokemon/egg_moves.h data
        if poke.egg_moves != None:
            out['egg_moves.h'][identifier] = list(poke.egg_moves)
        
        # src/data/pokemon/evolution.h data
        if poke.evo_target != None:
            if type(poke.evo_type) is LevelEvo:
                out['evolution.h'][identifier] = [['EVO_LEVEL', poke.evo_type.level, poke_to_id[poke.evo_target.name]]]
            elif type(poke.evo_type) is FriendshipEvo:
                out['evolution.h'][identifier] = [['EVO_FRIENDSHIP', 0, poke_to_id[poke.evo_target.name]]]
            elif type(poke.evo_type) is StoneEvo:
                out['evolution.h'][identifier] = [['EVO_ITEM', poke.evo_type.stone, poke_to_id[poke.evo_target.name]]]
            else:
                raise BaseException('unknown evolution type')
        
        # src/data/pokemon/level_up_learnsets.h data
        learnset = []
        for lvl, mv in poke.learnset:
            learnset.append([lvl, mv.name])
        out['level_up_learnsets.h'][ids_to_learnset_pointers[identifier]] = learnset
        
        # src/data/pokemon/tmhm_learnsets.h data
        out['tmhm_learnsets.h'][identifier] = list(poke.tms)
        
        # src/data/pokemon/tutor_learnsets.h data
        out['tutor_learnsets.h'][identifier] = list(poke.tutor_moves)
        
        # data for randomizing wild encounters
        if not (Flags.LEGENDARY in poke.flags or Flags.MYTHICAL in poke.flags or Flags.LEGENDARY_TRIO in poke.flags or Flags.FIRE_STARTER in poke.flags or Flags.WATER_STARTER in poke.flags or Flags.GRASS_STARTER in poke.flags):
            out['encounter_data'][identifier] = {
                'types' : poke.types,
                'egg_groups' : poke.egg_groups,
                'bst' : poke.bst
            }
        
    # src/data/text_species_names.h data
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        out['species_names.h'].append(poke.name.upper())
    
    # image colors
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        out['image_colors'].append(poke.image_colors)
    
    # src/data/pokemon/pokedex_entries.h data
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        dex_entry = {}
        dex_entry['categoryName'] = poke.category
        dex_entry['weight'] = poke.weight
        dex_entry['height'] = poke.height
        out['pokedex_entries.h'][index_to_id[str(index)]] = dex_entry
    
    # move data for trainer generation
    for move_name in move_data.keys():
        move = move_data[move_name]
        move_info = { 'type' : move.type, 'value' : move.value, 'damaging' : move.damaging }
        
        if not move.damaging:
            for role in status_move_usage_hints.keys():
                for dmg_cat in status_move_usage_hints[role].keys():
                    if move.effect in status_move_usage_hints[role][dmg_cat]:
                        move_info['usage_role'] = role
                        move_info['usage_category'] = dmg_cat
                        break
            if not 'usage_role' in move_info.keys():
                raise BaseException('no usage hint for ' + move_name + ' (' + move.effect + ')')
        
        out['moves'][move_name] = move_info
    
    # strategy for trainer generation
    out['strategy'] = {}
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        
        strat = {}
        hp, atk, df, spatk, spdf, spd = poke.stats
        
        atk_ratio = atk / spatk
        
        if atk_ratio >= 1.2:
            strat['damage_type'] = 'PHYSICAL'
            dmg_ratio = (2 * atk + spd) / (hp + df + spd)
        elif atk_ratio <= 0.8:
            strat['damage_type'] = 'SPECIAL'
            dmg_ratio = (2 * spatk + spd) / (hp + df + spd)
        else:
            strat['damage_type'] = 'MIXED'
            dmg_ratio = (atk + spatk + spd) / (hp + df + spd)
        
        if dmg_ratio >= 1.1:
            strat['role'] = 'OFFENSIVE'
        elif dmg_ratio <= 0.9:
            strat['role'] = 'DEFENSIVE'
        else:
            strat['role'] = 'MIXED'
        
        out['strategy'][index_to_id[str(index)]] = strat
    
    teachable_moves = []
    teachable_moves.extend(tm_list)
    teachable_moves.extend(tutor_move_list)
    teachable_moves.sort(key = lambda m: out['moves'][m]['value'])
    
    out['teachable_moves'] = teachable_moves
    
    with open('dex.json', 'w') as f:
        f.write(json.dumps(out, indent=2, sort_keys=False))
dex = debug_gen_dex()
output_to_json(dex)
