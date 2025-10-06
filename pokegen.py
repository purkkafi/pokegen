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
    ability_value = rawdb['ability_value']
    move_value_adjustment = rawdb['move_value_adjustment']
    status_move_usage_hints = rawdb['status_move_usage_hints']
    similar_move_sets = rawdb['similar_move_sets']
    treat_as_status_moves = rawdb['treat_as_status_moves']
    treat_as_damaging_moves = rawdb['treat_as_damaging_moves']
    tm_list = rawdb['tm_list']
    tutor_move_list = rawdb['tutor_move_list']
    universal_tms = rawdb['universal_tms']
    type_colors = rawdb['type_colors']
    average_weights = rawdb['average_weights']
    average_heights = rawdb['average_heights']
    generic_baby_namestrings = rawdb['generic_baby_namestrings']
    limited_moves = set(rawdb['limited_moves'])

# normalize type weights
type_weights_sum = sum(type_weights.values())

for tw in type_weights.keys():
    type_weights[tw] = type_weights[tw] / type_weights_sum

# normalize common type combos
common_type_combos = set()
for ctb in rawdb['common_type_combos']:
    common_type_combos.add(tuple(sorted(ctb)))

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
    
    chunk_extractor = re.compile(r'\[MOVE_(.+)\]\s=\n\s\s\s\s{([\s\S]+?)}')
    
    get_type = re.compile(r'type\s=\sTYPE_([A-Z]+)')
    get_power = re.compile(r'power\s=\s([0-9]+)')
    get_pp = re.compile(r'pp\s=\s([0-9]+)')
    get_effect = re.compile(r'effect\s=\sEFFECT_([A-Z0-9_]+)')
    get_accuracy = re.compile(r'accuracy\s=\s([0-9]+)')
    
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
        
        if is_damaging and name in treat_as_status_moves:
            is_damaging = False
        if not is_damaging and name in treat_as_damaging_moves:
            is_damaging = True
        
        move_data[name] = Move(name=name, type=move_type, value=move_value, damaging=is_damaging, power=move_power, effect=move_effect)
    
    return move_data

def sort_move_list(ls):
    ls = list(ls)
    ls.sort(key=lambda m: m.value)
    return ls

move_data = read_move_data()

def pkmn_complexity(themes):
    complexity = 0
    for theme in themes:
        data = themedata[theme]
        if 'necessary_types' in data:
            complexity = complexity + len(data['necessary_types']) * 10
        if 'possible_types' in data:
            complexity = complexity + len(data['possible_types']) * 5
        if 'moves' in data:
            complexity = complexity + min(15, len(data['moves']))
        if 'abilities' in data:
            complexity = complexity + min(5, len(data['abilities']))
    return complexity

class Habitat(Enum):
    LAND = auto()
    FOREST = auto()
    LAKE = auto()
    SHORE = auto()
    OCEAN = auto()
    SEAFLOOR = auto()
    CAVE = auto()
    CRAGGY = auto()
    MOUNTAIN = auto()
    URBAN = auto()
    DESERT = auto()
    
    def __repr__(self):
        return self.name

class Motif(Enum):
    DRAGONIC = auto()
    MYSTICAL = auto()
    POLLUTION = auto()
    UNDEAD = auto()
    ELECTRICAL = auto()
    VOLCANIC = auto()
    COLD = auto()
    FUNGAL = auto()
    ANIMAL = auto()
    CREATURE = auto()
    EARTHY = auto()
    PLANT = auto()
    
    def __repr__(self):
        return self.name

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
        self.habitats = None
        self.motifs = None
        self.pokedex_fr = None
        self.pokedex_ruby = None
    
    def __repr__(self):
        return f'[{self.name}]'
    
    # Recursively adds themes from initially defined ones
    def populate_themes(self):
        self.initial_themes = list(self.themes)
        
        self.optional_subthemes = []
        for theme in self.initial_themes:
            self.populate_theme(theme)
        
        while len(self.optional_subthemes) > 0:
            chosen = random.choice(self.optional_subthemes)
            
            if pkmn_complexity(list(self.themes) + [chosen]) > 80:
                break
            
            self.optional_subthemes.remove(chosen)
            self.populate_theme(chosen)
            
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
                self.optional_subthemes.append(optional_theme)
    
    # Generates data based on themes
    def generate(self):
        self.populate_themes()
        self.generate_name()
        self.generate_type()
        self.generate_abilities()
        self.generate_bst()
        self.generate_egg_groups()
        self.assign_base_stats()
        self.generate_moves()
        self.generate_learnset()
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
        self.generate_habitats_and_motifs()
    
    def evolve(self, bst_increase = 0):
        next_stage = Pokemon()
        next_stage.previous_stage = self
        next_stage.themes = self.themes
        next_stage.initial_themes = self.initial_themes
        next_stage.flags = set(self.flags)
        next_stage.bst_ability_adjustment = self.bst_ability_adjustment
        
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
        next_stage.generate_habitats_and_motifs()
        
        if Flags.LAST_EVOLVABLE_STAGE in self.flags:
            next_stage.flags.remove(Flags.LAST_EVOLVABLE_STAGE)
        
        if Flags.THREE_STAGES in self.flags and Flags.LAST_EVOLVABLE_STAGE not in self.flags:
            next_stage.flags.add(Flags.LAST_EVOLVABLE_STAGE)
        
        self.evo_target = next_stage
        adjust = int(10 * ((type_bsts[self.types[0]] + type_bsts[self.types[1]]) / 2))
        self.evo_type = LevelEvo(round(7 + adjust + 45 * ((self.bst-200)/300) ))
        
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
        
        if min_val != max_val:
            ability_adjust = 0
            for ab in self.abilities:
                if ab in ability_value:
                    ability_adjust += ability_value[ab]
            if self.abilities[1] != 'NONE':
                ability_adjust = int(ability_adjust / 2)
            
            self.bst_ability_adjustment = ability_adjust
        else:
            self.bst_ability_adjustment = 0
    
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
        
        self.name = None
        for i in range(1,50):
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
        
        if end_word == '':
            print('!!!!!! problem, no end word in', self.name)
    
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
        
        if 'TRUANT' in self.abilities:
            self.abilities = [ 'TRUANT', 'NONE' ]
        
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
                
                theme_moves = themedata[theme]['moves']
                for tm in themedata[theme]['moves']:
                    if tm in limited_moves and random.random() > 0.66:
                        theme_moves.remove(tm)
                
                theme_moves = random.sample(theme_moves, min(10, len(theme_moves)))
                
                for move in theme_moves:#themedata[theme]['moves']:
                    moves.add(move)
        
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
    
    def filter_moves(self, movelist, damaging, type_predicate, value_predicate):
        chosen = []
        for move in movelist:
            if move_data[move].damaging == damaging and type_predicate(move_data[move].type) and value_predicate(move_data[move].value):
                if not move in limited_moves or random.random() > 0.5:
                    chosen.append(move)
        return chosen
    
    def pick_with_predicate(self, from_list, predicate):
        pickable = [x for x in from_list if predicate(x)]
        if len(pickable) == 0:
            return None
        return random.choice(pickable)
    
    def pick_and_remove(self, from_list, into_set, excludes, predicate=lambda _: True):
        if len(from_list) == 0:
            print('\tfound none', from_list)
            return
        pick = self.pick_with_predicate(from_list, predicate)
        if pick == None:
            print('\tfound none', from_list)
            return
        
        while pick in excludes:
            from_list.remove(pick)
            pick = self.pick_with_predicate(from_list, predicate)
            if pick == None:
                print('\tfound none', from_list)
                return
        
        self.update_excludes(excludes, pick)
        from_list.remove(pick)
        into_set.add(pick)
        print('\t', pick)
    
    def update_excludes(self, excludes, new_move):
        for similar_set in similar_move_sets:
            for similar in similar_set:
                if new_move == similar:
                    excludes.update(similar_set)
                    return
    
    def generate_learnset(self):
        learnset = set()
        target_len = random.randint(9, 11)
        movelist = list(self.moves)
        
        if Flags.DITTO in self.flags:
            self.learnset = [(1, move_data['TRANSFORM'])]
            return
        
        # give starters more moves
        if Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags:
            target_len = random.randint(10, 11)
        
        offense = self.stats[1] + self.stats[3] + self.stats[5]
        defense = self.stats[0] + self.stats[2] + self.stats[4]
        
        nondmg_ratio = 0.45
        if offense/defense > 1.1:
            nondmg_ratio = 0.4
        elif offense/defense < 0.9:
            nondmg_ratio = 0.5
        
        dualtype = self.types[0] != self.types[1]
        stab_ratio = 0.75 if dualtype else 0.5
        
        bad_nondamaging = self.filter_moves(movelist, damaging=False, type_predicate=lambda t: True, value_predicate=lambda v: v <= 90)
        good_nondamaging = self.filter_moves(movelist, damaging=False, type_predicate=lambda t: True, value_predicate=lambda v: v > 90)
        bad_stab_dmg = self.filter_moves(movelist, damaging=True, type_predicate=lambda t: t in self.types, value_predicate=lambda v: v <= 85)
        good_stab_dmg = self.filter_moves(movelist, damaging=True, type_predicate=lambda t: t in self.types, value_predicate=lambda v: v > 85)
        bad_nonstab_dmg = self.filter_moves(movelist, damaging=True, type_predicate=lambda t: t not in self.types, value_predicate=lambda v: v <= 80)
        good_nonstab_dmg = self.filter_moves(movelist, damaging=True, type_predicate=lambda t: t not in self.types, value_predicate=lambda v: v > 80)
        
        excludes = set()
        
        print(self.types, nondmg_ratio)
        print(bad_stab_dmg, good_stab_dmg)
        
        for i in range(math.ceil(target_len * nondmg_ratio / 2)):
            self.pick_and_remove(bad_nondamaging, learnset, excludes)
            self.pick_and_remove(good_nondamaging, learnset, excludes)
        
        first_stab = True if random.random() > 0.5 else False
        pick_stab1 = lambda m: move_data[m].type == self.types[0]
        pick_stab2 = lambda m: move_data[m].type == self.types[1]
        for i in range(math.ceil(target_len * (1-nondmg_ratio) * (stab_ratio) / 2)):
            if random.random() > 0.25:
                first_stab = not first_stab
            self.pick_and_remove(bad_stab_dmg, learnset, excludes, predicate=(pick_stab1 if first_stab else pick_stab2))
            
            first_stab = not first_stab
            self.pick_and_remove(good_stab_dmg, learnset, excludes, predicate=(pick_stab1 if first_stab else pick_stab2))
        
        for i in range(math.ceil(target_len * (1-nondmg_ratio) * (1-stab_ratio) / 2)):
            self.pick_and_remove(bad_nonstab_dmg, learnset, excludes)
            self.pick_and_remove(good_nonstab_dmg, learnset, excludes)
        
        nondmg_leftovers = []
        nondmg_leftovers.extend(bad_nondamaging)
        nondmg_leftovers.extend(good_nondamaging)
        dmg_leftovers = []
        dmg_leftovers.extend(bad_stab_dmg)
        dmg_leftovers.extend(good_stab_dmg)
        dmg_leftovers.extend(bad_nonstab_dmg)
        dmg_leftovers.extend(good_nonstab_dmg)
        
        used_leftovers = dmg_leftovers
        tries = 0
        
        print('------------')
        while len(learnset) < target_len and tries < 100:
            self.pick_and_remove(used_leftovers, learnset, excludes)
            used_leftovers = dmg_leftovers if used_leftovers == nondmg_leftovers else nondmg_leftovers
            tries = tries+1
        
        # make sure starters have a good starting move
        if Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags:
            if 'SCRATCH' not in learnset and 'POUND' not in learnset and 'TACKLE' not in learnset:
                if 'SCRATCH' in movelist:
                    learnset.add('SCRATCH')
                elif 'POUND' in movelist:
                    learnset.add('POUND')
                else:
                    learnset.add('TACKLE')
                    if 'TACKLE' not in movelist:
                        movelist.append('TACKLE')
                        self.moves.add('TACKLE')
        
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
            if not dmg_cat and can_fix:
                learnset[i+2], learnset[i+3] = learnset[i+3], learnset[i+2]
        
        # transform list into tuples (level, move)
        if Flags.SINGLE in self.flags:
            if Flags.LEGENDARY in self.flags or Flags.MYTHICAL in self.flags or Flags.LEGENDARY_TRIO in self.flags:
                target_max_lvl = random.randint(70, 90)
            else:
                target_max_lvl = random.randint(45, 55)
                
        elif Flags.TWO_STAGES in self.flags: # bst 250–450
            lo = 47
            hi = 53
            d = (self.bst-250)/200
            target_max_lvl = int(hi*d + lo*(1-d))
            
        elif Flags.THREE_STAGES in self.flags: # bst 200–350
            lo = 35
            hi = 45
            d = (self.bst-200)/150
            target_max_lvl = int(hi*d + lo*(1-d))
        
        lvl_1_moves = random.randint(1,3)
        # no multiple damaging moves that share the same type in lvl 1 moves
        while True:
            ms = learnset[0:lvl_1_moves]
            types = []
            for m in ms:
                if m.damaging:
                    types.append(m.type)
            
            if len(types) != len(set(types)):
                lvl_1_moves = lvl_1_moves - 1
                continue
            
            break
        
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
        
        # avoid starters having elemental attacks before lvl 5
        if Flags.GRASS_STARTER in self.flags or Flags.FIRE_STARTER in self.flags or Flags.WATER_STARTER in self.flags:
            changed = False
            
            for index,mv in enumerate(learnset):
                lvl = mv[0]
                tp = mv[1].type
                if lvl <= 5 and (tp == 'GRASS' or tp == 'FIRE' or tp == 'WATER') and mv[1].damaging:
                    new_lvl = 6
                    old_lvl = lvl
                    
                    # find move to switch with
                    for index2,mv2 in enumerate(learnset):
                        lvl2 = mv2[0]
                        tp2 = mv2[1].type
                        if (lvl2 > 5 and lvl2 <= 10) and (not mv2[1].damaging or (tp2 != 'GRASS' and tp2 != 'FIRE' and tp2 != 'WATER')):
                            # switch these moves
                            new_lvl = lvl2
                            learnset[index2] = (old_lvl, mv2[1])
                            break
                    
                    # if no suitable move to switch with was found, set problematic attack to lvl6    
                    learnset[index] = (new_lvl, mv[1])
                    changed = True
            
            if changed:
                learnset.sort(key=lambda m: m[0])
        
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
        
        # adjust HP so that stat total matches target BST in case of rounding errors
        bst_diff = self.bst - sum(self.stats)
        self.stats[0] += bst_diff
        
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
            self.held_items = list(self.previous_stage.held_items)
        else:
            self.held_items = ['NONE', 'NONE']
        
        commons = []
        rares = []
        special_commons = []
        special_rares = []
        for theme in self.themes:
            if 'common_held_items' in themedata[theme]:
                commons.extend(themedata[theme]['common_held_items'])
            if 'special_common_held_items' in themedata[theme]:
                commons.extend(themedata[theme]['special_common_held_items'])
                special_commons.extend(themedata[theme]['special_common_held_items'])
            if 'rare_held_items' in themedata[theme]:
                rares.extend(themedata[theme]['rare_held_items'])
            if 'special_rare_held_items' in themedata[theme]:
                rares.extend(themedata[theme]['special_rare_held_items'])
                special_rares.extend(themedata[theme]['special_rare_held_items'])
        
        if self.held_items[0] == 'NONE':
            if random.random() >= 0.7 and len(commons) != 0:
                self.held_items[0] = random.choice(commons)
            elif len(special_commons) != 0:
                self.held_items[0] = random.choice(special_commons)
        
        if self.held_items[1] == 'NONE':
            if random.random() >= 0.7 and len(rares) != 0:
                self.held_items[1] = random.choice(rares)
            elif len(special_rares) != 0:
                self.held_items[1] = random.choice(special_rares)
        
        if random.random() >= 0.7:
            if self.held_items[1] == 'NONE' and self.held_items[0] != 'NONE':
                self.held_items[1] = self.held_items[0]
        
        if random.random() >= 0.5:
            if self.held_items[0] == 'NONE' and self.held_items[1] != 'NONE':
                self.held_items[0] = self.held_items[1]
    
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
        
        # theme average size
        theme_avg_size = None
        theme_sizes = []
        for t in self.themes:
            if 'size' in themedata[t]:
                ts_range = themedata[t]['size']
                theme_sizes.append(random.uniform(ts_range[0], ts_range[1]))
        if len(theme_sizes) != 0:
            theme_avg_size = sum(theme_sizes) / len(theme_sizes)
            # adjust because pokemon tend to be light and short
            theme_avg_size = theme_avg_size ** 0.9
        
        # determine weight
        type_avg_w = (average_weights[self.types[0]] + average_weights[self.types[1]])/2
        
        if theme_avg_size != None:
            avg_w = (type_avg_w + 9*theme_avg_size)/10
        else:
            avg_w = type_avg_w
        
        w = -1
        while w < 1:
            w = nprandom.normal(loc=avg_w, scale=avg_w)
        if w > 9999:
            w = 9999
        
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
        
        if theme_avg_size != None:
            # TODO think about the magic numbers
            h = (avg_h + 4*theme_avg_size*0.025444479931864154)/5
        
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

    def generate_habitats_and_motifs(self):
        if self.previous_stage != None:
            self.habitats = self.previous_stage.habitats
            self.motifs = self.previous_stage.motifs
            return
        
        habitats = defaultdict(lambda: 0)
        motifs = defaultdict(lambda: 0)
        
        for theme in self.themes:
            if 'habitat' in themedata[theme]:
                for hb in themedata[theme]['habitat']:
                    hb = Habitat[hb.upper()]
                    habitats[hb] = habitats[hb] + 1
        
        for theme in self.themes:
            if 'motif' in themedata[theme]:
                for mf in themedata[theme]['motif']:
                    mf = Motif[mf.upper()]
                    motifs[mf] = motifs[mf] + 1
        
        chosen_habitats = list(habitats.keys())
        random.shuffle(chosen_habitats)
        chosen_habitats.sort(key=lambda h: -habitats[h])
        self.habitats = chosen_habitats[0:random.randint(2,3)]
        
        chosen_motifs = list(motifs.keys())
        random.shuffle(chosen_motifs)
        chosen_motifs.sort(key=lambda m: -motifs[m])
        self.motifs = chosen_motifs[0:random.randint(2,3)]
    
    def primary_type(self):
        if Flags.WATER_STARTER in self.flags:
            return 'WATER'
        if Flags.GRASS_STARTER in self.flags:
            return 'GRASS'
        if Flags.FIRE_STARTER in self.flags:
            return 'FIRE'
        if self.types[0] == self.types[1]:
            return self.types[0]
        
        counts = {}
        counts[self.types[0]] = 0
        counts[self.types[1]] = 0
        for (lvl,mv) in self.learnset:
            if mv.type in counts.keys():
                counts[mv.type] = counts[mv.type] + 1
        
        return self.types[0] if counts[self.types[0]] > counts[self.types[1]] else self.types[1]
    
    def other_type(self):
        return self.types[1] if self.primary_type() == self.types[0] else self.types[0]

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
    return random.randint(30, 190)

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
        if type(possibilities) is dict:
            weights = list(untyped_themes)
            for i,tp in enumerate(untyped_themes):
                weights[i] = possibilities[tp]
            return random.choices(untyped_themes, weights)[0]
        else:
            return random.choice(untyped_themes)
    else:
        weights = []
        for theme in typed_themes:
            acc = 0
            for tp in result_types[theme]:
                acc = acc + type_weights[tp]
            acc = acc / len(result_types[theme])
            weights.append(acc)
        
        if type(possibilities) is dict:
            new_weights = list(weights)
            w_adj = sum(weights)
            p_adj = sum(possibilities.values())
            
            for i,tp in enumerate(typed_themes):
                new_weights[i] = (weights[i]/w_adj * possibilities[tp]/p_adj)
            return random.choices(typed_themes, new_weights)[0]
        else:
            return random.choices(typed_themes, weights)[0]

def init_dex_balance_data(dex_size):
    global used_combos, total_combos, expected_per_type, expected_monotypes
    used_combos = defaultdict(lambda: 0)
    total_combos = defaultdict(lambda: 0)
    
    expected_per_type = {}
    for tp in type_weights.keys():
        expected_per_type[tp] = int(dex_size * type_weights[tp])
    
    expected_monotypes = {}
    for tp in expected_per_type.keys():
        expected_monotypes[tp] = max(1, int(expected_per_type[tp] // 2.5))

def make_pkmn(slot, flags, dex_size, bst_range=(0,0), reroll=True):
    global used_combos, total_combos, expected_per_type, expected_monotypes
    pkmn = Pokemon(bst_range=bst_range, flags=flags)
    
    archetype = random.choice(archetypes)
    subarchetype = random.choice(subarchetypes)
    
    # might change (sub)archetype to something that matches missing types
    if not reroll:
        pkmn_per_type = {}
        
        for tp in type_weights:
            pkmn_per_type[tp] = 0
        
        for tc in used_combos:
            pkmn_per_type[tc[0]] = pkmn_per_type[tc[0]] + 1
            if tc[0] != tc[1]:
                pkmn_per_type[tc[1]] = pkmn_per_type[tc[1]] + 1
        
        limit = min(pkmn_per_type.values())
        if limit > 2:
            limit = 2
        
        for tp in type_weights:
            if pkmn_per_type[tp] > limit:
                del pkmn_per_type[tp]
        
        good_archetypes = set()
        for arch in archetypes:
            if 'necessary_types' in themedata[arch]:
                for nt in themedata[arch]['necessary_types']:
                    if nt in pkmn_per_type:
                        good_archetypes.add(arch)
        good_archetypes = list(good_archetypes)
        
        good_subarchetypes = set()
        for arch in subarchetypes:
            if 'necessary_types' in themedata[arch]:
                for nt in themedata[arch]['necessary_types']:
                    if nt in pkmn_per_type:
                        good_subarchetypes.add(arch)
        good_subarchetypes = list(good_subarchetypes)
        
        if len(good_archetypes) != 0:
            archetype = random.choice(good_archetypes)
        
        if len(good_subarchetypes) != 0:
            subarchetype = random.choice(good_subarchetypes)
    
    if Flags.WATER_STARTER in flags:
        archetype = random.choices(list(water_starter_archetypes.keys()), weights=water_starter_archetypes.values())[0]
        if archetype == 'water_animal':
            subarchetype = random.choice(subarchetypes)
        else:
            subarchetype = 'water_elemental'
    
    if Flags.FIRE_STARTER in flags:
        archetype = random.choices(list(fire_starter_archetypes.keys()), weights=fire_starter_archetypes.values())[0]
        subarchetype = 'fire_elemental'
    
    if Flags.GRASS_STARTER in flags:
        archetype = random.choices(list(grass_starter_archetypes.keys()), weights=grass_starter_archetypes.values())[0]
        if archetype == 'plant':
            subarchetype = random.choice(subarchetypes)
        else:
            subarchetype = 'grass_elemental'
    
    if Flags.FOSSIL in flags:
        subarchetype = 'rocky'
    
    if Flags.DITTO in flags:
        archetype = 'blob'
    
    if Flags.LEGENDARY_TRIO in flags or Flags.MYTHICAL in flags or Flags.LEGENDARY in flags:
        reroll = False
        if len(special_dex_slots[slot]) == 3:
            archetype = special_dex_slots[slot][2]
    
    pkmn.themes.add(archetype)
    pkmn.themes.add(subarchetype)
    
    pkmn.generate()
    
    type_combo = tuple(sorted(pkmn.types))
    
    reroll_conds = {
        'overused_combo': lambda tc: (tc[0] != tc[1]) and used_combos[tc] >= (4 if tc in common_type_combos else 2),
        'is_overused_monotype': lambda tc: (tc[0] == tc[1]) and used_combos[tc] >= expected_monotypes[tc[0]],
        'both_types_overused': lambda tc: (tc[0] != tc[1]) and total_combos[tc[0]] >= expected_per_type[tc[0]] and total_combos[tc[1]] >= expected_per_type[tc[1]],
        'type_sum_overused': lambda tc: (tc[0] != tc[1]) and (total_combos[tc[0]] + total_combos[tc[1]] >= expected_per_type[tc[0]] + expected_per_type[tc[1]] - 2)
    }
    
    if reroll:
        if any(cond(type_combo) for cond in reroll_conds.values()):
            #print('rerolling ', type_combo, ', '.join(cond + ': ' + str(reroll_conds[cond](type_combo)) for cond in reroll_conds))
            for i in range(0,10):
                pkmn = make_pkmn(slot, flags, dex_size, bst_range=bst_range, reroll=False)
                type_combo = tuple(sorted(pkmn.types))
                if all(not cond(type_combo) for cond in reroll_conds.values()):
                    break
                #else:
                #    print('  rejected', type_combo, ', '.join(cond + ': ' + str(reroll_conds[cond](type_combo)) for cond in reroll_conds))
            #print('  got', type_combo, ': ', pkmn.name)
    
    # update data used for rerolling
    if reroll:
        used_combos[type_combo] = used_combos[type_combo] + 1
        
        total_combos[type_combo[0]] = total_combos[type_combo[0]] + 1
        if type_combo[0] != type_combo[1]:
            total_combos[type_combo[1]] = total_combos[type_combo[1]] + 1
        
    return pkmn

ungainable_types = [ 'NORMAL', 'FLYING', 'BUG', 'WATER', 'GRASS', 'GROUND', 'ELECTRIC', 'FIRE' ]
rare_starter_secondary_types = [ 'GHOST', 'STEEL', 'ICE', 'DRAGON', 'ROCK', 'ELECTRIC' ]
impossible_starter_secondary_types = [ 'FIRE', 'WATER', 'GRASS', 'NORMAL' ]

general_starter_archetypes = { 'small_animal': 4, 'dark_animal': 1, 'ground_animal': 1, 'monster': 1, 'humanoid_fighter': 1, 'humanoid_psychic': 1, 'bird': 1 }
fire_starter_archetypes = dict(general_starter_archetypes)
water_starter_archetypes = dict(general_starter_archetypes)
water_starter_archetypes['water_animal'] = 4
grass_starter_archetypes = dict(general_starter_archetypes)
water_starter_archetypes['plant'] = 4


# no evo: 350–500
# stage 1 of 3: 200–350 // + 100–125 per evo
# stage 1 of 2: 250–450 // + 100–150
def generate_family(slot, evo_cat, dex_size, special=None, used_starter_subtypes=set()):
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
        
        pkmn = make_pkmn(slot, flags, dex_size, bst_range=bst_range)
        
        if not special == Flags.DITTO:
            pkmn.tms.add('HYPER_BEAM')
        return [ pkmn ]
        
    elif evo_cat == Flags.TWO_STAGES:
        flags.add(Flags.LAST_EVOLVABLE_STAGE)
        pkmn = make_pkmn(slot, flags, dex_size, bst_range=(250, 450))
        pkmn2 = pkmn.evolve(bst_increase=random.randint(100, 150))
        
        primtype = pkmn.primary_type()
        if primtype != pkmn.other_type() and random.random() > 0.6 and not pkmn.other_type() in ungainable_types:
            pkmn.types = [primtype, primtype]
        
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
        
        pkmn = make_pkmn(slot, flags, dex_size, bst_range=bst_range)
        
        if special == Flags.FIRE_STARTER or special == Flags.GRASS_STARTER or special == Flags.WATER_STARTER:
            while (pkmn.primary_type() != pkmn.other_type() and pkmn.other_type() in impossible_starter_secondary_types) or pkmn.other_type() in used_starter_subtypes:
                pkmn = make_pkmn(slot, flags, dex_size, bst_range=bst_range)
            used_starter_subtypes.add(pkmn.other_type())
        
        pkmn2 = pkmn.evolve(bst_increase=bst_increase_1)
        pkmn3 = pkmn2.evolve(bst_increase=bst_increase_2)
        
        primtype = pkmn.primary_type()
        if primtype != pkmn.other_type() and random.random() > 0.6 and not pkmn.other_type() in ungainable_types:
            pkmn.types = [primtype, primtype]
            pkmn2.types = [primtype, primtype]
        
        if special == Flags.FIRE_STARTER or special == Flags.GRASS_STARTER or special == Flags.WATER_STARTER:
            if pkmn3.other_type() in rare_starter_secondary_types:
                pkmn.types = [primtype, primtype]
        
        pkmn3.tms.add('HYPER_BEAM')
        return [ pkmn, pkmn2, pkmn3 ]

special_dex_slots = [None] * 412
special_dex_slots[1] = (Flags.THREE_STAGES, Flags.GRASS_STARTER) # kanto starters
special_dex_slots[4] = (Flags.THREE_STAGES, Flags.FIRE_STARTER)
special_dex_slots[7] = (Flags.THREE_STAGES, Flags.WATER_STARTER)

special_dex_slots[137] = (Flags.SINGLE, Flags.DITTO) # ditto

special_dex_slots[138] = (Flags.TWO_STAGES, Flags.FOSSIL) # fossil line 1
special_dex_slots[140] = (Flags.TWO_STAGES, Flags.FOSSIL) # fossil line 2
special_dex_slots[142] = (Flags.SINGLE, Flags.FOSSIL) # aerodactyl
special_dex_slots[143] = (Flags.SINGLE, None) # snorlax

legendary_birds_arch = random.choice(archetypes) # legendary birds
special_dex_slots[144] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)
special_dex_slots[145] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)
special_dex_slots[146] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_birds_arch)

special_dex_slots[147] = (Flags.THREE_STAGES, Flags.PSEUDO) # pseudo (dratini)

mews_arch = random.choice(archetypes)
special_dex_slots[150] = (Flags.SINGLE, Flags.LEGENDARY, mews_arch) # mewtwo
special_dex_slots[151] = (Flags.SINGLE, Flags.MYTHICAL, mews_arch) # mew

special_dex_slots[152] = (Flags.THREE_STAGES, Flags.GRASS_STARTER) # johto starters
special_dex_slots[155] = (Flags.THREE_STAGES, Flags.FIRE_STARTER)
special_dex_slots[158] = (Flags.THREE_STAGES, Flags.WATER_STARTER)

legendary_beasts_arch = random.choice(archetypes) # legendary beasts
special_dex_slots[243] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_beasts_arch)
special_dex_slots[244] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_beasts_arch)
special_dex_slots[245] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, legendary_beasts_arch)

special_dex_slots[246] = (Flags.THREE_STAGES, Flags.PSEUDO) # pseudo (larvitar)

tower_duo_arch = random.choice(archetypes) # tower duo
special_dex_slots[249] = (Flags.SINGLE, Flags.LEGENDARY, tower_duo_arch) # lugia
special_dex_slots[250] = (Flags.SINGLE, Flags.LEGENDARY, tower_duo_arch) # ho-oh

special_dex_slots[251] = (Flags.SINGLE, Flags.MYTHICAL) # celebi

special_dex_slots[277] = (Flags.THREE_STAGES, Flags.GRASS_STARTER) # hoenn starters
special_dex_slots[280] = (Flags.THREE_STAGES, Flags.FIRE_STARTER)
special_dex_slots[283] = (Flags.THREE_STAGES, Flags.WATER_STARTER)

special_dex_slots[388] = (Flags.TWO_STAGES, Flags.FOSSIL) # hoenn fossil line 1
special_dex_slots[390] = (Flags.TWO_STAGES, Flags.FOSSIL) # hoenn fossil line 2

special_dex_slots[392] = (Flags.THREE_STAGES, None) # ralts line, hardcoding to avoid trouble

special_dex_slots[395] = (Flags.THREE_STAGES, Flags.PSEUDO) # pseudo (bagon)
special_dex_slots[398] = (Flags.THREE_STAGES, Flags.PSEUDO) # pseudo (beldum)

regi_arch = random.choice(archetypes) # regi trio
special_dex_slots[401] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, regi_arch)
special_dex_slots[402] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, regi_arch)
special_dex_slots[403] = (Flags.SINGLE, Flags.LEGENDARY_TRIO, regi_arch)

special_dex_slots[404] = (Flags.SINGLE, Flags.LEGENDARY) # kyogre
special_dex_slots[405] = (Flags.SINGLE, Flags.LEGENDARY) # groudon
special_dex_slots[406] = (Flags.SINGLE, Flags.LEGENDARY) # rayquaza

lati_arch = random.choice(archetypes) # lati@s
special_dex_slots[407] = (Flags.SINGLE, Flags.MYTHICAL, lati_arch)
special_dex_slots[408] = (Flags.SINGLE, Flags.MYTHICAL, lati_arch)

special_dex_slots[409] = (Flags.SINGLE, Flags.MYTHICAL) # jirachi
special_dex_slots[410] = (Flags.SINGLE, Flags.MYTHICAL) # deoxys

special_dex_slots[411] = (Flags.SINGLE, None) # chimecho as a special cse

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

def gen_dex(start_index, end_index, sort_start=None, sort_end=None):
    dex = []
    index = start_index
    dex_size = end_index - start_index
    init_dex_balance_data(dex_size)
    used_starter_subtypes = set()
    
    while index < end_index:
        index = start_index + len(dex)
        
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
        
        pks = generate_family(index, evo_cat, dex_size, special, used_starter_subtypes)
        dex.extend(pks)
    
    if sort_start == None and sort_end == None:
        return dex
    
    # approximately sort dex by bst
    sorting = list(dex[sort_start-1:sort_end])
    sorting.sort(key=lambda pk: dex_sort_key(pk))
    dex[sort_start-1:sort_end] = sorting
    
    return dex

index_to_id = {}

get_id = re.compile(r'SPECIES_(\S+)\s([0-9]+)')
with open(pokered_folder + '/include/constants/species.h') as f:
    species_h = f.read()
for line in species_h.split('\n'):
    m = get_id.search(line)
    if m != None:
        index_to_id[m.group(2)] = m.group(1)

def output_to_json(dex, ndex, hdex):

    poke_to_id = {}
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        poke_to_id[poke if type(poke) is str else poke.name] = index_to_id[str(index)]
    
    pokedex_fr = {}
    
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
        'encounter_list_kanto' : [],
        'encounter_list_kanto_post' : [],
        'encounter_list_hoenn' : [],
        'moves' : {},
        'teachable_moves' : [],
        'pokedex_entries.h' : {},
        'pokedex_text_fr.h' : {},
        'national_dex' : ndex,
        'hoenn_dex' : hdex
    }
    
    ids_to_learnset_pointers = {}
    get_pointer = re.compile(r'\[SPECIES_(\S+)\]\s=\s(.+),')
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
        
        if type(poke) is str:
            entry = 'OLD_UNOWN'
        else:
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
        if not type(poke) is str and poke.egg_moves != None:
            out['egg_moves.h'][identifier] = list(poke.egg_moves)
        
        # src/data/pokemon/evolution.h data
        if not type(poke) is str and poke.evo_target != None:
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
        if type(poke) is str:
            learnset.append([1, 'TACKLE'])
        else:
            for lvl, mv in poke.learnset:
                learnset.append([lvl, mv.name])
        out['level_up_learnsets.h'][ids_to_learnset_pointers[identifier]] = learnset
        
        if not type(poke) is str:
            # src/data/pokemon/tmhm_learnsets.h data
            out['tmhm_learnsets.h'][identifier] = list(poke.tms)
            
            # src/data/pokemon/tutor_learnsets.h data
            out['tutor_learnsets.h'][identifier] = list(poke.tutor_moves)
        
        # pokedex entries
        if not type(poke) is str:
            out['pokedex_text_fr.h'][identifier] = poke.pokedex_fr
        
        # data for randomizing wild encounters
        if not type(poke) is str:
            
            out['encounter_data'][identifier] = {
                    'habitats' : [h.name for h in poke.habitats],
                    'motifs' : [m.name for m in poke.motifs],
                    'bst' : poke.bst,
                    'types' : poke.types,
                    'egg_groups' : poke.egg_groups
                }
            
            if (Flags.LEGENDARY in poke.flags or Flags.MYTHICAL in poke.flags or Flags.LEGENDARY_TRIO in poke.flags or Flags.FIRE_STARTER in poke.flags or Flags.WATER_STARTER in poke.flags or Flags.GRASS_STARTER in poke.flags):
                continue
            
            if ndex.index(identifier) <= 151: # mon in kanto dex
                out['encounter_list_kanto'].append(identifier)
            
            if ndex.index(identifier) <= 251: # mon in kanto or johto dex
                out['encounter_list_kanto_post'].append(identifier)
            
            if hdex.index(identifier) <= 202: # mon in hoenn dex
                out['encounter_list_hoenn'].append(identifier)
        
    # src/data/text_species_names.h data
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        if type(poke) is str:
            out['species_names.h'].append('?')
        else:
            out['species_names.h'].append(poke.name.upper())
    
    # image colors
    for index, poke in enumerate(dex):
        if poke == None:
            continue
        if type(poke) is str:
            out['image_colors'].append('OLD_UNOWN')
        else:
            out['image_colors'].append(poke.image_colors)
    
    # src/data/pokemon/pokedex_entries.h data
    for index, poke in enumerate(dex):
        if poke == None or type(poke) is str:
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
        if poke == None or type(poke) is str:
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

def output_dex_txt(dex):
    string = []
    
    for i in range(1, len(dex)):
        poke = dex[i]
        if type(poke) is str:
            string.append(f'{i}: {poke}')
            continue
        string.append(f'{i}: {poke.name.ljust(15)}\t{str(poke.types).ljust(30)}\t{poke.abilities}\t({index_to_id[str(i)]})')
        string.append(f'\t{poke.name_start} + {poke.name_end}, {poke.themes}')
        string.append(f'\tstats: {poke.stats}, bst: {sum(poke.stats)}')
        string.append(f'\tcatch rate: {poke.catch_rate}, gender ratio: {poke.gender_ratio}, base friendship: {poke.base_friendship}, flee rate: {poke.flee_rate}')
        string.append(f'\thabitats: {poke.habitats}, motifs: {poke.motifs}')
        string.append(f'\tegg groups: {poke.egg_groups}, egg cycles: {poke.egg_cycles}, growth rate: {poke.growth_rate}')
        string.append(f'\texp yield: {poke.exp_yield}, ev yield: {poke.ev_yield}, held items: {poke.held_items}')
        string.append(f'\tbody color: {poke.body_color}, category: {poke.category}, weight: {poke.weight/10} kg, height: {poke.height/10} m')
        string.append(f'\t"{poke.pokedex_fr}" (FR)')
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

def print_type_spread(dex):
    # debug print for type spread
    families = set()
    for poke in dex[1:]:
        if type(poke) is str:
            continue
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
        print(f'\t{tp}: {type_spread[tp]}')
        
        spread_str = ""
        for combo in combo_spread.keys():
            if combo[0] != tp and combo[1] != tp:
                continue
            spread_str += f'\t{combo_spread[combo]} {"*" if combo[0] == tp else combo[0]}/{"*" if combo[1] == tp else combo[1]}\n'
        #print(spread_str)
    
    #print(', '.join(tp + ': ' + str(type_spread[tp]) for tp in type_spread.keys()))
    rare_types = []
    for tp in type_weights.keys():
        if type_spread[tp] < 5:
            rare_types.append(f'{tp} ({type_spread[tp]})')
    print('rare types:', ', '.join(rare_types))

"""
Returns the tuple (ndex, hdex), containing all
the Pokémon in National Dex and Hoenn Dex orders.
"""
def generate_dex_orders(dex):
    original = {}
    for i,pk in enumerate(dex):
        original[pk] = index_to_id[str(i)]
    original['NONE'] = 'NONE'
    
    chimecho = dex[-1]
    sorting_hdex = dex[286:395]
    sorting_hdex.append(chimecho)
    
    hdex_start = dex[277:286]
    hdex_end = dex[395:411]
    
    old_families = []
    bad_flags = (Flags.GRASS_STARTER, Flags.FIRE_STARTER, Flags.WATER_STARTER, Flags.MYTHICAL, Flags.LEGENDARY, Flags.LEGENDARY_TRIO)
    for poke in dex[1:251]:
        if poke.previous_stage == None:
            has_bad_flag = False
            for bf in bad_flags:
                if bf in poke.flags:
                    has_bad_flag = True
            
            if has_bad_flag:
                continue
            
            family = [ poke ]
            while poke.evo_target != None:
                poke = poke.evo_target
                family.append(poke)
            
            old_families.append(family)
    
    pk_of_tp = defaultdict(lambda: list())
    for pk in sorting_hdex:
        tp = tuple(sorted(pk.types))
        pk_of_tp[tp[0]].append(tp)
        if tp[0] != tp[1]:
            pk_of_tp[tp[1]].append(tp)
    
    prelength = len(hdex_start) + len(hdex_end)
    while True:
        family = random.choice(old_families)
        
        if len(sorting_hdex) + prelength + len(family) > 202:
            continue
        
        tp = tuple(sorted(family[-1].types))
        if len(pk_of_tp[tp[0]]) >= 10 or len(pk_of_tp[tp[1]]) >= 10:
            if (len(pk_of_tp[tp[0]]) >= 6 and len(pk_of_tp[tp[1]]) >= 6) and random.random() > 0.33:
                continue
        
        pk_of_tp[tp[0]].append(tp)
        if tp[0] != tp[1]:
            pk_of_tp[tp[1]].append(tp)
        
        old_families.remove(family)
        sorting_hdex.extend(family)
        
        if len(sorting_hdex) + prelength == 202:
            break
    
    sorting_hdex.sort(key=lambda pk: dex_sort_key(pk))
    
    hdex = [ 'NONE' ]
    hdex.extend(hdex_start)
    hdex.extend(sorting_hdex)
    hdex.extend(hdex_end)
    
    print('Hoenn dex type spread:')
    print_type_spread(hdex)
    
    for pk in dex[1:]:
        if type(pk) is str:
            continue
        if pk not in hdex:
            hdex.append(pk)
    
    ndex = dex[0:252]
    
    for hpk in hdex[1:]:
        if not hpk in ndex:
            ndex.append(hpk)
    
    # convert to names of original pokemon
    for i,pk in enumerate(ndex):
        ndex[i] = original[pk]
    
    for i,pk in enumerate(hdex):
        hdex[i] = original[pk]
    
    return (ndex, hdex)


# returns whether predator mon can predate on prey mon
def can_eat(predator, prey):
    if predator == prey:
        return False
    
    # can't eat legends
    if Flags.LEGENDARY in prey.flags or Flags.MYTHICAL in prey.flags or Flags.LEGENDARY_TRIO in prey.flags:
        return False
    
    common_habitat = False
    for h in predator.habitats:
        if h in prey.habitats:
            common_habitat = True
            break
    
    if not common_habitat:
        return False
    
    # make sure prey is not too large
    w_ratios = []
    for t in predator.themes:
        if 'prey_size_ratio' in themedata[t]:
            w_ratios.append(themedata[t]['prey_size_ratio'])
    if len(w_ratios) == 0:
        w_ratio = 0.75
    else:
        w_ratio = sum(w_ratios) / len(w_ratios)
    
    if prey.weight > predator.weight * w_ratio:
        return False
    
    # make sure prey is not too small
    if prey.weight < predator.weight * 0.01:
        return False
    
    return True

# generates pokedex entries
get_keywords = re.compile('\\[(.+?)\\]')
def generate_dex_entries(mons):
    for mon in mons:
        words = {}
        
        can_evolve = mon.evo_target != None
        
        # select place
        places = []
        for p in mon.habitats + mon.motifs:
            if p.name in rawdb['dex_places']:
                places.extend(rawdb['dex_places'][p.name])
        for t in mon.themes:
            if 'dex_place' in themedata[t]:
                places.extend(themedata[t]['dex_place'])
        words['PLACE'] = random.choice(places)
        
        # select food
        foods = []
        for t in mon.themes:
            if 'dex_food' in themedata[t]:
                foods.extend(themedata[t]['dex_food'])
        if len(foods) != 0:
            words['FOOD'] = random.choice(foods)
        
        # select prey
        prey_themes = []
        for t in mon.themes:
            if 'dex_prey' in themedata[t]:
                prey_themes.extend(themedata[t]['dex_prey'])
        
        preys = []
        for prey in mons:
            test_prey = False
            for pt in prey_themes:
                if pt in prey.themes:
                    test_prey = True
                    break
            
            if test_prey and can_eat(mon, prey):
                preys.append(prey.name)
        
        if len(preys) != 0:
            words['PREY'] = random.choice(preys)
        
        # only food or prey
        if 'FOOD' in words and 'PREY' in words:
            if random.random() >= 0.25:
                words.pop('FOOD')
            else:
                words.pop('PREY')
        
        # select action
        actions = []
        for t in mon.themes:
            if 'dex_action' in themedata[t]:
                actions.extend(themedata[t]['dex_action'])
        if len(actions) != 0:
            action = random.choice(actions)
            words['ACTION-ING'] = action['ing']
            words['ACTION-3RD'] = action['3rd']
        
        # select attack noun
        attack_nouns = []
        for t in mon.themes:
            if 'dex_attack_noun' in themedata[t]:
                attack_nouns.extend(themedata[t]['dex_attack_noun'])
        if len(attack_nouns) != 0:
            words['ATTACK-NOUN'] = random.choice(attack_nouns)
        
        # select feeling adjective
        feeling_adjs = []
        for t in mon.themes:
            if 'dex_adj_feeling' in themedata[t]:
                feeling_adjs.extend(themedata[t]['dex_adj_feeling'])
        if len(feeling_adjs) != 0:
            words['ADJ-FEELING'] = random.choice(feeling_adjs)
        
        # select body adjective
        body_adjs = []
        for t in mon.themes:
            if 'dex_adj_body' in themedata[t]:
                body_adjs.extend(themedata[t]['dex_adj_body'])
        if len(body_adjs) != 0:
            words['ADJ-BODY'] = random.choice(body_adjs)
        
        # select kind
        kinds = []
        for t in mon.themes:
            if 'dex_kind' in themedata[t]:
                kinds.extend(themedata[t]['dex_kind'])
        if len(kinds) != 0:
            words['KIND'] = random.choice(kinds)
        
        # select brings
        if not can_evolve:
            brings = []
            for t in mon.themes:
                if 'dex_brings' in themedata[t]:
                    brings.extend(themedata[t]['dex_brings'])
            if len(brings) != 0:
                words['BRINGS'] = random.choice(brings)
        
        # generate entry
        phrases = list(rawdb['dex_phrases'])
        entry = ''
        tries = 0
        while len(entry) <= 70 and tries <= 10 and len(phrases) >= 1:
            tries = tries + 1
            phrase = random.choice(phrases)
            phrases.remove(phrase)
            
            keywords = get_keywords.findall(phrase)
            valid = True
            for kw in keywords:
                if kw in words:
                    phrase = phrase.replace('['+kw+']', words[kw])
                else:
                    valid = False
            
            if valid and len(entry + ' ' + phrase) <= 90:
                phrase = phrase[0].capitalize() + phrase[1:]
                entry += (' ' + phrase)
                for kw in keywords:
                    words.pop(kw)
            
        entry = entry.strip()
        
        mon.pokedex_fr = entry

dex = [None]

# kanto dex
dex.extend(kanto_mons := gen_dex(1, 151, sort_start=10, sort_end=137))

# TODO experimental, johto dex
dex.extend(johto_mons := gen_dex(152, 251, sort_start=161, sort_end=246))

# old unown incides
dex.extend(['OLD_UNOWN'] * 25)

# TODO experimental, hoenn dex
dex.extend(hoenn_mons := gen_dex(277, 411)) # note: no need to sort because that is done seperately for the pokedex order

print('Kanto dex type spread:')
print_type_spread(kanto_mons)

ndex, hdex = generate_dex_orders(dex)

# do bst_ability_adjustment
for pk in dex:
    if pk != None and (type(pk) != str) and pk.bst_ability_adjustment != 0:
        diff = int(pk.bst_ability_adjustment // -6)
        for i in range(len(pk.stats)):
            pk.stats[i] += diff

generate_dex_entries(kanto_mons)
generate_dex_entries(johto_mons)
generate_dex_entries(hoenn_mons)

output_dex_txt(dex)
output_to_json(dex, ndex, hdex)
