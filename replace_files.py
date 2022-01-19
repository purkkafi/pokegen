#!/usr/bin/python3

import re
import json
import sys
import random
from enum import Enum, auto

if(len(sys.argv) != 2):
    print('usage: replace_files.py [path to pokefirered folder]')
    exit()

pokered_folder = sys.argv[1]

class MonContext(Enum):
    UNKNOWN = auto()
    WILD = auto()
    TRAINER = auto()
    BOSS = auto()

with open('dex.json') as f:
    dex = json.load(f)

def generate_base_stats_h():
    with open('templates/base_stats.h_template') as f:
        template = f.read()
        
    poke_start = re.compile('\s\s\s\s\[SPECIES_(.+)\]\s=')
    poke_end = re.compile('\s\s\s\s\},')
    
    data = dex['base_stats.h']
    
    current_poke = None
    
    output = []
    
    for line in template.split('\n'):
        m = poke_start.search(line)
        
        if m != None and m.group(1) in data:
            current_poke = m.group(1)
            output.append(line)
            output.append('    {')
            
            pkmn = data[current_poke]
            
            output.append(
f"""        .baseHP = {pkmn['baseHP']},
        .baseAttack = {pkmn['baseAttack']},
        .baseDefense = {pkmn['baseDefense']},
        .baseSpeed = {pkmn['baseSpeed']},
        .baseSpAttack = {pkmn['baseSpAttack']},
        .baseSpDefense = {pkmn['baseSpDefense']},
        .type1 = TYPE_{pkmn['type1']},
        .type2 = TYPE_{pkmn['type2']},
        .catchRate = {pkmn['catchRate']},
        .expYield = {pkmn['expYield']},
        .evYield_HP = {pkmn['evYield_HP']},
        .evYield_Attack = {pkmn['evYield_Attack']},
        .evYield_Defense = {pkmn['evYield_Defense']},
        .evYield_Speed = {pkmn['evYield_Speed']},
        .evYield_SpAttack = {pkmn['evYield_SpAttack']},
        .evYield_SpDefense = {pkmn['evYield_SpDefense']},
        .item1 = ITEM_{pkmn['item1']},
        .item2 = ITEM_{pkmn['item2']},
        .genderRatio = {pkmn['genderRatio']},
        .eggCycles = {pkmn['eggCycles']},
        .friendship = {pkmn['friendship']},
        .growthRate = GROWTH_{pkmn['growthRate']},
        .eggGroup1 = EGG_GROUP_{pkmn['eggGroup1']},
        .eggGroup2 = EGG_GROUP_{pkmn['eggGroup2']},
        .abilities = {{ ABILITY_{pkmn['abilities'][0]}, ABILITY_{pkmn['abilities'][1]} }},
        .safariZoneFleeRate = {pkmn['safariZoneFleeRate']},
        .bodyColor = BODY_COLOR_{pkmn['bodyColor']},
        .noFlip = TRUE,""")
        
        if poke_end.search(line) != None:
            current_poke = None
        
        if current_poke == None:
            output.append(line)
    
    with open(pokered_folder + '/src/data/pokemon/base_stats.h', 'w') as f:
        f.write('\n'.join(output))
    
    print('wrote /src/data/pokemon/base_stats.h')

def generate_names_h():
    with open('templates/species_names.h_template') as f:
        template = f.read()
    
    names = dex['species_names.h']
    names.insert(0, '??????????')
    is_name = re.compile('\s\s\s\s_\("(.+)"\)')
    
    output = []
    
    index = 0
    
    for line in template.split('\n'):
        m = is_name.search(line)
        if m == None:
            output.append(line)
        else:
            if index < len(names):
                output.append(f'    _("{names[index]}"),')
            else:
                output.append(line)
            index = index + 1
    
    with open(pokered_folder + '/src/data/text/species_names.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/text/species_names.h')

def generate_pokemon_h():
    with open('templates/pokemon.h_template') as f:
        template = f.read()
    
    with open('templates/palette_template') as f:
        palette_template = f.read()
    
    get_front_pic = re.compile('const\su32\s(.+)\s=\sINCBIN_U32\("graphics\/pokemon\/(.+)\/front.4bpp.lz"\);')
    get_back_pic = re.compile('const\su32\s(.+)\s=\sINCBIN_U32\("graphics\/pokemon\/(.+)\/back.4bpp.lz"\);')
    get_icon = re.compile('const\su8\s(.+)\s=\sINCBIN_U8\("graphics\/pokemon\/(.+)\/icon.4bpp"\);')
    get_palette = re.compile('const\su32\s.+\s=\sINCBIN_U32\(\"(.+)normal\.gbapal\.lz"\);')
    
    output = []
    
    colors = dex['image_colors']
    index = 1
    
    for line in template.split('\n'):
        m_front = get_front_pic.search(line)
        m_back = get_back_pic.search(line)
        m_icon = get_icon.search(line)
        m_palette = get_palette.search(line)
        
        if '_Egg[]' in line:
            m_front = m_palette = m_icon = None
        
        if m_palette != None and index <= 151:
            palette_file = f'{pokered_folder}{m_palette.group(1)}normal.pal'
            color0 = colors[index-1][0]
            color255 = colors[index-1][1]
            
            color205 = (int(205/255*color255[0] + (255-205)/255*color0[0]), int(205/255*color255[1] + (255-205)/255*color0[1]), int(205/255*color255[2] + (255-205)/255*color0[2]))
            color172 = (int(172/255*color255[0] + (255-172)/255*color0[0]), int(172/255*color255[1] + (255-172)/255*color0[1]), int(172/255*color255[2] + (255-172)/255*color0[2]))
            
            palette = palette_template
            palette = palette.replace('0 0 0', f'{color0[0]} {color0[1]} {color0[2]}')
            palette = palette.replace('172 172 172', f'{color172[0]} {color172[1]} {color172[2]}')
            palette = palette.replace('205 205 205', f'{color205[0]} {color205[1]} {color205[2]}')
            palette = palette.replace('255 255 255', f'{color255[0]} {color255[1]} {color255[2]}')
            
            index = index + 1
            
            with open(palette_file, 'wb') as f:
                f.write(str.encode(palette.replace('\n', '\r\n')))
        
        if m_front != None:
            output.append(f'const u32 {m_front.group(1)} = INCBIN_U32("graphics/pokemon/question_mark/circled/front.4bpp.lz");')
        elif m_back != None:
            output.append(f'const u32 {m_back.group(1)} = INCBIN_U32("graphics/pokemon/question_mark/circled/back.4bpp.lz");')
        elif m_icon != None:
            output.append(f'const u8 {m_icon.group(1)} = INCBIN_U8("graphics/pokemon/question_mark/icon.4bpp");')
        else:
            output.append(line)
    with open(pokered_folder + '/src/data/graphics/pokemon.h', 'w') as f:
        f.write('\n'.join(output))
    
    print('wrote /src/data/graphics/pokemon.h')

def generate_egg_moves_h():
    with open('templates/egg_moves.h_template') as f:
        template = f.read()
    
    data = dex['egg_moves.h']
    output = []
    is_start = re.compile('\s\s\s\segg_moves\((.+),')
    
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        if len(data[poke]) != 0:
            movelist = ', '.join([ '\n              MOVE_'+mv for mv in data[poke] ])
            output.append(f'    egg_moves({poke}, {movelist}),\n')
    
    output.append(tmpl_end)
    
    with open(pokered_folder + '/src/data/pokemon/egg_moves.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/egg_moves.h')

def generate_tmhm_learnsets_h():
    with open('archetypes.json') as f:
        tm_list = json.load(f)['tm_list']
    
    tms = {}
    
    for i, tm in enumerate(tm_list):
        index = i+1
        if index <= 50:
            start = f'TM{str(index).rjust(2, "0")}'
        else:
            start = f'HM{str(index-50).rjust(2, "0")}'
        if tm == 'SOLAR_BEAM':
            tm_str = 'SOLARBEAM'
        else:
            tm_str = tm
        tms[tm] = f'{start}_{tm_str}'
    
    with open('templates/tmhm_learnsets.h_template') as f:
        template = f.read()
    
    data = dex['tmhm_learnsets.h']
    output = []
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        if len(data[poke]) != 0:
            learnset = "\n                                        | ".join([ "TMHM(" + tms[tm] + ")" for tm in data[poke] ])
            output.append(f'    [SPECIES_{poke}] = TMHM_LEARNSET({learnset}),\n')
    
    output.append(tmpl_end)
    
    with open(pokered_folder + 'src/data/pokemon/tmhm_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/tmhm_learnsets.h')

def generate_tutor_learnsets_h():
    with open('templates/tutor_learnsets.h_template') as f:
        template = f.read()
    
    data = dex['tutor_learnsets.h']
    output = []
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        if len(data[poke]) != 0:
            learnset = '\n                        | '.join([ f'TUTOR(MOVE_{mv})' for mv in data[poke] ])
            output.append(f'    [SPECIES_{poke}] = {learnset},\n')
    
    output.append(tmpl_end)
    
    with open(pokered_folder + 'src/data/pokemon/tutor_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/tutor_learnsets.h')

def generate_pokedex_entries_h():
    with open('templates/pokedex_entries.h_template') as f:
        template = f.read()
    
    species_def = re.compile('DEX_(.+)\]')
    
    output = []
    current_species = None
    
    for line in template.split('\n'):
        m = species_def.search(line)
        
        if m != None:
            if m.group(1) in dex['pokedex_entries.h'].keys():
                current_species = m.group(1)
            else:
                current_species = None
        
        if current_species != None:
            
            if 'category' in line:
                output.append(f"        .categoryName = _(\"{dex['pokedex_entries.h'][current_species]['categoryName']}\"),")
                continue
            
            if 'height' in line:
                output.append(f"        .height = {dex['pokedex_entries.h'][current_species]['height']},")
                continue
            
            if 'weight' in line:
                output.append(f"        .weight = {dex['pokedex_entries.h'][current_species]['weight']},")
                continue
            
            if 'pokemonScale' in line:
                output.append('        .pokemonScale = 256,')
                continue
            
            if 'pokemonOffset' in line:
                output.append('        .pokemonOffset = 0,')
                continue
            
            if 'trainerScale' in line:
                output.append('        .trainerScale = 256,')
                continue
            
            if 'trainerOffset' in line:
                output.append('        .trainerOffset = 0,')
                continue
        
        output.append(line)
    
    with open(pokered_folder + 'src/data/pokemon/pokedex_entries.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote src/data/pokemon/pokedex_entries.h')


def generate_pokedex_text_fr_h():
    with open('templates/pokedex_text_fr.h_template') as f:
        template = f.read()
    
    blank_entry = """_(
    "This is a newly discovered POKéMON. It is\\n"
    "currently under investigation. No detailed\\n"
    "information is available at this time.")"""
    
    output = re.sub('_\(\n.+\n.+\n.+\)', lambda x: blank_entry, template)
    
    with open(pokered_folder + 'src/data/pokemon/pokedex_text_fr.h', 'w') as f:
        f.write(output)
    print('wrote src/data/pokemon/pokedex_text_fr.h')

def evo_string(evo):
    if evo[0] == 'EVO_LEVEL':
        return f'{{EVO_LEVEL, {evo[1]}, SPECIES_{evo[2]}}}'
    if evo[0] == 'EVO_ITEM':
        return f'{{EVO_ITEM, ITEM_{evo[1]}, SPECIES_{evo[2]}}}'
    if evo[0] == 'EVO_FRIENDSHIP':
        return f'{{EVO_FRIENDSHIP, 0, SPECIES_{evo[2]}}}'
    
def generate_evolution_h():
    with open('templates/evolution.h_template') as f:
        template = f.read()
    
    data = dex['evolution.h']
    output = []
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        value = '{' + ', '.join([ (evo_string(evo)) for evo in data[poke] ]) + '}'
        output.append(f'    [SPECIES_{poke}]  = {value},\n')
    
    output.append(tmpl_end)
    
    with open(pokered_folder + 'src/data/pokemon/evolution.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/evolution.h')

def generate_level_up_learnsets_h():
    with open('templates/level_up_learnsets.h_template') as f:
        template = f.read()
    
    poke_start = re.compile('static\sconst\su16\s(.+)\[\]')
    output = []
    data = dex['level_up_learnsets.h']
    current_poke = None
    
    for line in template.split('\n'):
        m = poke_start.search(line)
        
        if line == '};':
            current_poke = None
        elif m != None:
            current_poke = m.group(1)
            
            if current_poke in data:
                output.append(f'static const u16 {current_poke}[] = {{')
                for mv in data[current_poke]:
                    output.append(f'    LEVEL_UP_MOVE({mv[0]}, MOVE_{mv[1]}),')
                output.append('    LEVEL_UP_END')
        
        if current_poke == None or (not current_poke in data):
            output.append(line)
        
    with open(pokered_folder + 'src/data/pokemon/level_up_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote src/data/pokemon/level_up_learnsets.h')

def generate_sprite_position_files():
    with open(pokered_folder + 'src/data/pokemon_graphics/enemy_mon_elevation.h', 'w') as f:
        with open('templates/enemy_mon_elevation.h_template') as t:
            f.write(t.read())
    print('wrote src/data/pokemon_graphics/enemy_mon_elevation.h')
    
    with open(pokered_folder + 'src/data/pokemon_graphics/back_pic_coordinates.h', 'w') as f:
        with open('templates/back_pic_coordinates.h_template') as t:
            f.write(t.read())
    print('wrote src/data/pokemon_graphics/back_pic_coordinates.h.h')
    
    with open(pokered_folder + 'src/data/pokemon_graphics/front_pic_coordinates.h', 'w') as f:
        with open('templates/front_pic_coordinates.h_template') as t:
            f.write(t.read())
    print('wrote src/data/pokemon_graphics/front_pic_coordinates.h')

def filter_mons(of_types, of_egg_groups, max_lvl, ctxt=MonContext.UNKNOWN):
    choices = []
    
    if of_types == None and of_egg_groups == None:
        choices.extend(dex['encounter_data'].keys())
    else:
        for poke_name in dex['encounter_data'].keys():
            poke = dex['encounter_data'][poke_name]
            if poke['types'][0] in of_types or poke['types'][1] in of_types or poke['egg_groups'][0] in of_egg_groups or poke['egg_groups'][1] in of_egg_groups:
                choices.append(poke_name)
    
    choices.sort(key=lambda pk: dex['encounter_data'][pk]['bst'])
    
    rarity = max_lvl/50
    target_len = int(len(choices) * rarity)
    if target_len < 2:
        target_len = 2
    if target_len > len(choices):
        target_len = len(choices)
    
    choices = choices[0:target_len]
    
    random.shuffle(choices)
    
    if ctxt == MonContext.BOSS:
        target_len = 6
        if(len(choices) > 6):
            choices.sort(key=lambda pk: dex['encounter_data'][pk]['bst'])
            choices = choices[len(choices)-6:]
    else:
        target_len = random.randint(3, 5)
        
        if target_len > len(choices):
            target_len = len(choices)
        
        choices = choices[0:target_len]
    
    if len(choices) == 0:
        raise BaseException(f'no mons for {of_types}, {of_egg_groups}')
    
    return choices

evos_into = {}
evos_from = {}

for evolver in dex['evolution.h'].keys():
    evo = dex['evolution.h'][evolver][0]
    buffer = 25 #WAS 30
    if evolver in evos_from:
        buffer = evos_from[evolver]['at'] + 15
    
    if evo[0] == 'EVO_LEVEL':
        evos_into[evolver] = { 'at' : evo[1], 'to' : evo[2], 'wild' : True }
        evos_from[evo[2]] = { 'at' : evo[1], 'from' : evolver }
    elif evo[0] == 'EVO_ITEM':
        evos_into[evolver] = { 'at' : buffer, 'to' : evo[2], 'wild' : False }
        evos_from[evo[2]] = { 'at' : buffer, 'from' : evolver }
    elif evo[0] == 'EVO_FRIENDSHIP':   
        evos_into[evolver] = { 'at' : buffer, 'to' : evo[2], 'wild' : False }
        evos_from[evo[2]] = { 'at' : buffer, 'from' : evolver }
    
    # prevent stage 3 in wild
    if evolver in evos_into and evolver in evos_from:
        evos_into[evolver]['wild'] = False

def adjust_evo(mon, min_lvl, max_lvl=None, ctxt=None):
    if max_lvl == None:
        max_lvl = min_lvl
    
    mon_start = mon
    
    while mon in evos_into and max_lvl > evos_into[mon]['at']:
            mon = evos_into[mon]['to']
    while mon in evos_from and min_lvl < evos_from[mon]['at']:
            mon = evos_from[mon]['from']
    
    # prevent illegal wild evolutions
    if ctxt == MonContext.WILD and mon in evos_from:
        prev_stage = evos_from[mon]['from']
        if not evos_into[prev_stage]['wild']:
            mon = prev_stage
    
    # randomly devolve trainer pokemon close to evolution level
    if ctxt == MonContext.TRAINER and mon in evos_from:
        if max_lvl - 5 < evos_from[mon]['at']:
            if random.random() > 0.5:
                mon = evos_from[mon]['from']
    
    # bosses can cheat a bit and evolve pokemon earlier, as a treat
    if ctxt == MonContext.BOSS and mon in evos_into:
        if max_lvl + 4 >= evos_into[mon]['at']:
            mon = evos_into[mon]['to']
    
    if mon != mon_start:
        #print(f'lvl {min_lvl}–{max_lvl}: {mon_start} -> {mon}')
        if mon in evos_into:
            #print('\t', mon, evos_into[mon])
            pass
        if mon in evos_from:
            #print('\t', mon, evos_from[mon])
            pass
    
    return mon


def assign_wild_mons(types, egg_groups, wild_mons):
    max_lvl = max([ mon['max_level'] for mon in wild_mons['mons'] ])

    mons = filter_mons(types, egg_groups, max_lvl)

    for mon in wild_mons['mons']:
        mon['species'] = 'SPECIES_' + adjust_evo(random.choice(mons), mon['min_level'], mon['max_level'], ctxt=MonContext.WILD)

def try_generate_wild_encounters():
    with open('templates/wild_encounters.json_template') as f:
        encs = json.load(f)
    
    with open('encounter_data.json') as f:
        enc_data = json.load(f)
    
    for entry in encs['wild_encounter_groups'][0]['encounters']:
        map_name = entry['map']
        #print(map_name)
        
        if 'land_mons' in entry:
            types = enc_data[map_name]['types']
            egg_groups = enc_data[map_name]['egg_groups']
            
            assign_wild_mons(types, egg_groups, entry['land_mons'])
            
        if 'water_mons' in entry:
            types = enc_data['SPECIAL_SURFING']['types']
            egg_groups = enc_data['SPECIAL_SURFING']['egg_groups']
            
            assign_wild_mons(types, egg_groups, entry['water_mons'])
        
        if 'fishing_mons' in entry:
            types = enc_data['SPECIAL_FISHING']['types']
            egg_groups = enc_data['SPECIAL_FISHING']['egg_groups']
            
            assign_wild_mons(types, egg_groups, entry['fishing_mons'])
        
        if 'rock_smash_mons' in entry:
            types = enc_data['SPECIAL_ROCK_SMASH']['types']
            egg_groups = enc_data['SPECIAL_ROCK_SMASH']['egg_groups']
            
            assign_wild_mons(types, egg_groups, entry['rock_smash_mons'])
    
    return encs

def base_form(pkmn):
    while pkmn in evos_from:
        pkmn = evos_from[pkmn]['from']
    return pkmn

def pick_rare_pkmn(unavailable_families, available_families, req_type=None):
    if len(unavailable_families) != 0:
        rnd = random.choice(unavailable_families)
        unavailable_families.remove(rnd)
        return rnd
    
    if req_type == None:
        return random.choice(available_families)
    else:
        sel = random.choice(available_families)
        while not req_type in dex['encounter_data'][sel]['types']:
            sel = random.choice(available_families)
        return sel

def generate_wild_encounters():
    encs = try_generate_wild_encounters()
    
    spawns = set()
    
    for entry in encs['wild_encounter_groups'][0]['encounters']:
        if entry['base_label'].endswith('_FireRed'):
            if 'land_mons' in entry:
                for mon in entry['land_mons']['mons']:
                    spawns.add(mon['species'])
            if 'water_mons' in entry:
                for mon in entry['water_mons']['mons']:
                    spawns.add(mon['species'])
            if 'fishing_mons' in entry:
                for mon in entry['fishing_mons']['mons']:
                    spawns.add(mon['species'])
            if 'rock_smash_mons' in entry:
                for mon in entry['rock_smash_mons']['mons']:
                    spawns.add(mon['species'])
    
    available_families = set()
    special_families = set([ 'BULBASAUR', 'CHARMANDER', 'SQUIRTLE', 'ARTICUNO', 'ZAPDOS', 'MOLTRES', 'MEWTWO', 'MEW' ])
    unavailable_families = set()
    
    for poke in dex['base_stats.h'].keys():
        if base_form(poke) in special_families:
            continue
        
        if f'SPECIES_{poke}' in spawns:
            available_families.add(base_form(poke))
        
        if not base_form(poke) in available_families:
            unavailable_families.add(base_form(poke))
    
    available_families = list(available_families)
    unavailable_families = list(unavailable_families)
    
    print("unavailable families now:", unavailable_families)
    
    # replace lapras gift
    with open(pokered_folder + 'data/maps/SilphCo_7F/scripts.inc', 'w') as f:
        with open('templates/SilphCo_7F_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_LAPRAS', 'SPECIES_'+pick_rare_pkmn(unavailable_families, available_families))
        f.write(tmp)
        print('wrote /data/maps/SilphCo_7F/scripts.inc')
    
    # replace eevee gift
    with open(pokered_folder + 'data/maps/CeladonCity_Condominiums_RoofRoom/scripts.inc', 'w') as f:
        with open('templates/CeladonCity_Condominiums_RoofRoom_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_EEVEE', 'SPECIES_'+pick_rare_pkmn(unavailable_families, available_families))
        f.write(tmp)
        print('wrote /data/maps/CeladonCity_Condominiums_RoofRoom/scripts.inc')
    
    # replace magikarp gift
    with open(pokered_folder + 'data/maps/Route4_PokemonCenter_1F/scripts.inc', 'w') as f:
        with open('templates/Route4_PokemonCenter_1F_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_MAGIKARP', 'SPECIES_'+pick_rare_pkmn([], available_families))
        f.write(tmp)
        print('wrote /data/maps/Route4_PokemonCenter_1F/scripts.inc')
    
    # replace hitmon gift
    with open(pokered_folder + 'data/maps/SaffronCity_Dojo/scripts.inc', 'w') as f:
        with open('templates/SaffronCity_Dojo_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_HITMONCHAN', 'SPECIES_'+pick_rare_pkmn([], available_families, req_type='FIGHTING'))
            tmp = tmp.replace('SPECIES_HITMONLEE', 'SPECIES_'+pick_rare_pkmn([], available_families, req_type='FIGHTING'))
        f.write(tmp)
        print('wrote /data/maps/SaffronCity_Dojo/scripts.inc')
    
    # replace hypno encounter
    with open(pokered_folder + 'data/maps/ThreeIsland_BerryForest/scripts.inc', 'w') as f:
        with open('templates/ThreeIsland_BerryForest_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_HYPNO', 'SPECIES_'+adjust_evo(pick_rare_pkmn([], available_families, req_type='PSYCHIC'), 30))
        f.write(tmp)
        print('wrote /data/maps/ThreeIsland_BerryForest/scripts.inc')
    
    # replace togepi egg gift
    with open(pokered_folder + 'data/maps/FiveIsland_WaterLabyrinth/scripts.inc', 'w') as f:
        with open('templates/FiveIsland_WaterLabyrinth_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_TOGEPI', 'SPECIES_'+pick_rare_pkmn(unavailable_families, available_families))
        f.write(tmp)
        print('wrote /data/maps/FiveIsland_WaterLabyrinth/scripts.inc')
    
    # change roamer to mew
    with open(pokered_folder + 'src/roamer.c', 'w') as f:
        with open('templates/roamer.c_template') as t:
            tmp = t.read().replace('SPECIES_ENTEI', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_RAIKOU', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_SUICUNE', 'SPECIES_MEW')
        f.write(tmp)
        print('wrote /src/roamer.c')
    
    # replace game corner prizes
    with open(pokered_folder + 'data/maps/CeladonCity_GameCorner_PrizeRoom/scripts.inc', 'w') as f:
        with open('templates/CeladonCity_GameCorner_PrizeRoom_scripts.inc_template') as t:
            tmp = t.read()
            
            tmp = tmp.replace('SPECIES_ABRA', '[[$1$]]')
            tmp = tmp.replace('SPECIES_CLEFAIRY', '[[$2$]]')
            tmp = tmp.replace('SPECIES_SCYTHER', '[[$3$]]')
            tmp = tmp.replace('SPECIES_PINSIR', '[[$3$]]')
            tmp = tmp.replace('SPECIES_DRATINI', '[[$4$]]')
            tmp = tmp.replace('SPECIES_PORYGON', '[[$5$]]')
            
            tmp = tmp.replace('[[$1$]]', 'SPECIES_'+pick_rare_pkmn(unavailable_families, available_families))
            tmp = tmp.replace('[[$2$]]', 'SPECIES_'+pick_rare_pkmn(unavailable_families, available_families))
            tmp = tmp.replace('[[$3$]]', 'SPECIES_SQUIRTLE')
            tmp = tmp.replace('[[$4$]]', 'SPECIES_CHARMANDER')
            tmp = tmp.replace('[[$5$]]', 'SPECIES_BULBASAUR')
        f.write(tmp)
        print('wrote /data/maps/CeladonCity_GameCorner_PrizeRoom/scripts.inc')
    
    # replace in-game trades
    get_trade_species = re.compile('\s+\.species\s=\s(.+),')
    get_wanted_species = re.compile('\s+\.requestedSpecies\s=\s(.+)')
    trades_h_out = []
    with open('templates/ingame_trades.h_template') as f:
        for line in f.read().split('\n'):
            m_trade = get_trade_species.search(line)
            m_wanted = get_wanted_species.search(line)
            if m_trade != None:
                unav = unavailable_families
                if 'NIDO' in m_trade.group(1):
                    unav = []
                trades_h_out.append(f'        .species = SPECIES_{pick_rare_pkmn(unav, available_families)},')
            elif m_wanted != None:
                trades_h_out.append(f'        .requestedSpecies = SPECIES_{pick_rare_pkmn([], available_families)}')
            else:
                trades_h_out.append(line)
    
    with open(pokered_folder + 'src/data/ingame_trades.h', 'w') as f:
        f.write('\n'.join(trades_h_out))
    print('wrote /src/data/ingame_trades.h')
    
    print('final unavailable families:', unavailable_families)
    
    with open(pokered_folder + 'src/data/wild_encounters.json', 'w') as f:
        f.write(json.dumps(encs, indent=2, sort_keys=False))

special_types = ['FIRE', 'WATER', 'GRASS', 'ELECTRIC', 'PSYCHIC', 'ICE', 'DRAGON', 'DARK']
physical_types = ['NORMAL', 'FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL']

# until some kind of combo mechanism is invented
ai_forbidden_moves = [ 'DREAM_EATER', 'NIGHTMARE' ]

def assign_moves(species, level, signature_tm=None):
    available = set()
    
    ptr = dex['base_stats.h'][species]['__learnset_pointer']
    for mv in dex['level_up_learnsets.h'][ptr]:
        if mv[0] <= level:
            available.add(mv[1])
    
    teachable = dex['teachable_moves']
    end_index = min(len(teachable), int((level-10)/50 * len(teachable)))
    available_bonus = set(available)
    
    for mv in teachable[0:end_index]:
        if mv in dex['tmhm_learnsets.h'][species] or mv in dex['tutor_learnsets.h'][species]:
            available_bonus.add(mv)
    
    if level >= 30:
        available_bonus.update(dex['egg_moves.h'][base_form(species)])
    
    if signature_tm != None and signature_tm in dex['tmhm_learnsets.h'][species]:
        available.add(signature_tm)

    moves_bonus = list(available_bonus)
    moves_bonus.sort(key=by_move_value)
    moves_bonus = moves_bonus[0:int(len(moves_bonus) * min(1, level/40))]
    available.update(moves_bonus)
    
    for forbidden in ai_forbidden_moves:
        if forbidden in available:
            available.remove(forbidden)
    
    moves = list(available)
    
    if len(moves) <= 4:
        while len(moves) < 4:
            moves.append('NONE')
        return moves
    
    chosen = set()
    
    strat = dex['strategy'][species]
    
    if strat['role'] == 'OFFENSIVE':
        status_amount = random.randint(0,1)
    elif strat['role'] == 'DEFENSIVE':
        status_amount = random.randint(2,3)
    else:
        status_amount = random.randint(1,2)
    
    dmg_amount = 4 - status_amount
    
    for i in range(0, status_amount):
        m = pick_good_non_damaging(species, moves, strat['role'], strat['damage_type'], already_chosen=chosen)
        if m != None:
            chosen.add(m)
    
    stab_types = set(dex['encounter_data'][species]['types'])
    for i in range(0, 4 - len(chosen)):
        avoid_types = []
        
        if strat['damage_type'] == 'PHYSICAL':
            avoid_types.extend(special_types)
        elif strat['damage_type'] == 'SPECIAL':
            avoid_types.extend(physical_types)
        
        for stab in stab_types:
            if stab in avoid_types:
                avoid_types.remove(stab)
        
        for move in chosen:
            if dex['moves'][move]['damaging']:
                avoid_types.append(dex['moves'][move]['type'])
        
        m = pick_good_damaging(species, moves, avoid_types, stab_types, already_chosen=chosen)
        if m != None:
            chosen.add(m)
    
    while len(chosen) < 4:
        chosen = list(chosen)
        chosen.append('NONE')
    
    chosen = list(chosen)[0:4]
    
    # use signature move unless they have something better
    if signature_tm != None and dex['moves'][signature_tm]['damaging'] and not signature_tm in chosen:
        for index, move in enumerate(chosen):
            if dex['moves'][move]['damaging'] and dex['moves'][move]['type'] == dex['moves'][signature_tm]['type'] and dex['moves'][move]['value'] < dex['moves'][signature_tm]['value']:
                chosen[index] = signature_tm
                break
    
    return list(chosen)

by_move_value = lambda m: dex['moves'][m]['value']

def by_move_value_prefer_types(types):
    adjustment = lambda m: 1.5 if dex['moves'][m]['type'] in types else 1
    return lambda m: dex['moves'][m]['value'] * adjustment(m)

def pick_good_damaging(species, moves, avoid_types=[], prefer_types=[], already_chosen=[]):
    damaging = []
    
    for m in moves:
        if m in already_chosen:
            continue
        if dex['moves'][m]['damaging'] and (not dex['moves'][m]['type'] in avoid_types):
            damaging.append(m)
    
    damaging.sort(key=by_move_value_prefer_types(prefer_types))
    damaging = damaging[max(0,len(damaging)-3):len(damaging)]
    
    if len(damaging) == 0:
        if len(avoid_types) != 0:
            instead = pick_good_damaging(species, moves, avoid_types=[], prefer_types=[])
            return instead
        else:
            return None
    return random.choice(damaging)

overused_nondmg_attacks = [ 'REST', 'TOXIC', 'SUBSTITUTE', 'SNATCH', 'ROAR', 'COUNTER' ]

def pick_good_non_damaging(species, moves, role, category, already_chosen=[]):
    nondamaging = []
    
    for m in moves:
        if m in already_chosen:
            continue
        
        if not dex['moves'][m]['damaging']:
            
            if role == 'OFFENSIVE':
                if dex['moves'][m]['usage_role'] == 'DEFENSIVE':
                    continue
                elif dex['moves'][m]['usage_category'] != category:
                    continue
            elif role == 'DEFENSIVE':
                if dex['moves'][m]['usage_role'] == 'OFFENSIVE':
                    continue
            
            nondamaging.append(m)
    
    nondamaging.sort(key=by_move_value)
    nondamaging = nondamaging[max(0,len(nondamaging)-random.randint(6,12)):len(nondamaging)]
    
    # might not pick these because otherwise they're spammed everywhere
    #for ou in overused_nondmg_attacks:
    #    if ou in nondamaging and random.random() > 0.33:
    #        nondamaging.remove(ou)
    
    if len(nondamaging) == 0:
        return None
    return random.choice(nondamaging)

def generate_rival_teams():
    global grass_team
    global fire_team
    global water_team
    bird = base_form(random.choice(filter_mons(['FLYING'], [], 10)))
    
    grass_mon = base_form(random.choice(filter_mons(['GRASS'], [], 50)))
    water_mon = base_form(random.choice(filter_mons(['WATER'], [], 50)))
    fire_mon = base_form(random.choice(filter_mons(['FIRE'], [], 50)))
    
    psy_mon = base_form(random.choice(filter_mons(['PSYCHIC'], [], 50)))
    rock_mon = base_form(random.choice(filter_mons(['ROCK'], [], 50)))
    
    grass_team = [ rock_mon, water_mon, fire_mon,  psy_mon, bird, 'BULBASAUR' ]
    fire_team =  [ rock_mon, grass_mon, water_mon, psy_mon, bird, 'CHARMANDER' ]
    water_team = [ rock_mon, fire_mon,  grass_mon, psy_mon, bird, 'SQUIRTLE' ]
    
    if len(grass_team) != len(set(grass_team)) or len(fire_team) != len(set(fire_team)) or len(water_team) != len(set(water_team)):
        generate_rival_teams()

defensive_items = [ 'ITEM_BRIGHT_POWDER', 'ITEM_FOCUS_BAND', 'ITEM_LEFTOVERS', 'ITEM_LUM_BERRY', 'ITEM_SITRUS_BERRY', 'ITEM_WHITE_HERB' ]
physical_offensive_items = [ 'ITEM_KINGS_ROCK', 'ITEM_QUICK_CLAW', 'ITEM_SALAC_BERRY', 'ITEM_SCOPE_LENS', 'ITEM_LIECHI_BERRY' ]
special_offensive_items = [ 'ITEM_KINGS_ROCK', 'ITEM_QUICK_CLAW', 'ITEM_SALAC_BERRY', 'ITEM_SCOPE_LENS', 'ITEM_PETAYA_BERRY' ]

type_items = {
    'FIGHTING' : 'ITEM_BLACK_BELT',
    'DARK' : 'ITEM_BLACKGLASSES',
    'FIRE' : 'ITEM_CHARCOAL',
    'DRAGON' : 'ITEM_DRAGON_FANG',
    'ROCK' : 'ITEM_HARD_STONE',
    'ELECTRIC' : 'ITEM_MAGNET',
    'STEEL' : 'ITEM_METAL_COAT',
    'GRASS' : 'ITEM_MIRACLE_SEED',
    'WATER' : 'ITEM_MYSTIC_WATER',
    'ICE' : 'ITEM_NEVER_MELT_ICE',
    'POISON' : 'ITEM_POISON_BARB',
    'FLYING' : 'ITEM_SHARP_BEAK',
    'NORMAL' : 'ITEM_SILK_SCARF',
    'BUG' : 'ITEM_SILVER_POWDER',
    'GROUND' : 'ITEM_SOFT_SAND',
    'GHOST' : 'ITEM_SPELL_TAG',
    'PSYCHIC' : 'ITEM_TWISTED_SPOON'
}

def generate_trainers():
    global grass_team
    global fire_team
    global water_team
    
    trainer_start = re.compile('\s+\[TRAINER_')
    get_name = re.compile('\s+\.trainerName\s=\s_\("(.+)"\),')
    get_id = re.compile('(sTrainerMons_.+)}')
    get_class = re.compile('\s+\.trainerClass\s=\s(.+),')
    
    trainer_data = {}
    
    with open('class_data.json') as f:
        class_data = json.load(f)
    
    with open(pokered_folder + 'src/data/trainers.h') as f:
        for line in f.read().split('\n'):
            if trainer_start.search(line) != None:
                party_id = name = trainer_class = None
            
            m = get_name.search(line)
            if m != None:
                name = m.group(1)
            
            m = get_class.search(line)
            if m != None:
                trainer_class = m.group(1)
            
            m = get_id.search(line)
            if m != None and name != None and not (trainer_class in class_data['unused_classes']):
                trainer_id = m.group(1)
                trainer_data[trainer_id] = { 'name' : name, 'class' : trainer_class, 'id' : trainer_id }
    
    with open('templates/trainer_parties.h_template') as f:
        parties_h = f.read()
    
    party_start = re.compile('static\sconst\sstruct\s.+\s(sTrainerMons_.+)\[\]')
    party_species = re.compile('\s+\.species\s=\s(.+),')
    party_moves = re.compile('\s+\.moves\s=\s(.+),')
    party_lvl = re.compile('\s+\.lvl\s=\s(.+),')
    party_item = re.compile('\s+.heldItem\s=\s(.+),')
    
    parties_h_out = []
    current_trainer = None
    current_level = None
    current_species = None
    current_mon_count = None
    dupes = set()
    for line in parties_h.split('\n'):
        m = party_start.search(line)
        
        if m != None:
            if m.group(1) in trainer_data:
                current_trainer = trainer_data[m.group(1)]
            else:
                current_trainer = None
                current_level = None
                current_species = None
            current_mon_count = 0
            dupes.clear()
            
        
        m_sp = party_species.search(line)
        m_mv = party_moves.search(line)
        m_lvl = party_lvl.search(line)
        m_item = party_item.search(line)
        
        if m_sp != None and current_trainer != None:
            if current_trainer['class'] in class_data['special_classes']:
                if current_trainer['name'] in class_data['special_type_preference']:
                    mons = filter_mons(class_data['special_type_preference'][current_trainer['name']], [], current_level+15, ctxt=MonContext.BOSS)
                    #print('for', current_trainer['name'], mons, 'dupes:', dupes)
                    for mon in list(mons):
                        if base_form(mon) in dupes:
                            mons.remove(mon)
                            #print("won't dupe", mon)
                    if len(mons) == 0:
                        mons = filter_mons(class_data['special_type_preference'][current_trainer['name']], [], current_level+15, ctxt=MonContext.BOSS)
                elif current_trainer['name'] == 'TERRY':
                    if current_trainer['id'].startswith('sTrainerMons_RivalOaksLab'):
                        offset = 5
                    elif current_trainer['id'].startswith('sTrainerMons_RivalRoute22Early'):
                        offset = 4
                    elif current_trainer['id'].startswith('sTrainerMons_RivalCerulean'):
                        offset = 2
                    elif current_trainer['id'].startswith('sTrainerMons_RivalSsAnne'):
                        offset = 2
                    elif current_trainer['id'].startswith('sTrainerMons_RivalPokenonTower'):
                        offset = 1
                    elif current_trainer['id'].startswith('sTrainerMons_RivalSilph'):
                        offset = 1
                    else:
                        offset = 0
                    
                    if current_trainer['id'].endswith('Squirtle'):
                        mons = [ water_team[current_mon_count + offset] ]
                    elif current_trainer['id'].endswith('Charmander'):
                        mons = [ fire_team[current_mon_count + offset] ]
                    elif current_trainer['id'].endswith('Bulbasaur'):
                        mons = [ grass_team[current_mon_count + offset] ]
                        
            elif current_trainer['name'] in class_data['gym_trainers'].keys():
                gym_trainer_type = class_data['gym_trainers'][current_trainer['name']]
                mons = filter_mons(gym_trainer_type, [], current_level)
                
            else:
                tr_class = class_data['classes'][current_trainer['class']]
                mons = filter_mons(tr_class['types'], tr_class['egg_groups'], current_level)
            
            is_boss = current_trainer['class'] in class_data['special_classes']    
            mon = adjust_evo(random.choice(mons), current_level, ctxt=(MonContext.BOSS if is_boss else MonContext.TRAINER))
            
            current_species = mon
            dupes.add(base_form(mon))
            parties_h_out.append(f'        .species = SPECIES_{mon}, // {dex["base_stats.h"][mon]["type1"]}/{dex["base_stats.h"][mon]["type2"]}, role {dex["strategy"][mon]["role"]}, damage_type {dex["strategy"][mon]["damage_type"]}')
            current_mon_count = current_mon_count+1
        elif m_mv != None and current_trainer != None:
            signature_tm = None
            if current_trainer['name'] in class_data['signature_tm']:
                signature_tm = class_data['signature_tm'][current_trainer['name']]
            moves = assign_moves(current_species, current_level, signature_tm=signature_tm)
            parties_h_out.append(f'        .moves = {{MOVE_{moves[0]}, MOVE_{moves[1]}, MOVE_{moves[2]}, MOVE_{moves[3]}}},')
        elif m_lvl != None and current_trainer != None:
            current_level = int(m_lvl.group(1))
            parties_h_out.append(line)
        elif m_item != None and current_trainer != None and current_trainer['class'] in class_data['special_classes']:
            items = set()
            
            for tp in dex['encounter_data'][current_species]['types']:
                items.add(type_items[tp])
            
            if dex['strategy'][current_species]['role'] != 'OFFENSIVE':
                items.update(defensive_items)
            
            if dex['strategy'][current_species]['role'] != 'DEFENSIVE':
                if dex['strategy'][current_species]['damage_type'] != 'PHYSICAL':
                    items.update(special_offensive_items)
                if dex['strategy'][current_species]['damage_type'] != 'SPECIAL':
                    items.update(physical_offensive_items)
            
            parties_h_out.append(f'        .heldItem = {random.choice(list(items))},')
        else:
            parties_h_out.append(line)
    
    with open(pokered_folder + 'src/data/trainer_parties.h', 'w') as f:
        f.write('\n'.join(parties_h_out))
    print('wrote /src/data/trainer_parties.h')
    
generate_base_stats_h()
generate_names_h()
generate_pokemon_h()
generate_egg_moves_h()
generate_tmhm_learnsets_h()
generate_tutor_learnsets_h()
generate_evolution_h()
generate_level_up_learnsets_h()
generate_wild_encounters()
generate_pokedex_entries_h()
generate_pokedex_text_fr_h()
generate_sprite_position_files()

# hack: remove shitty moves/moves the AI can't really use before generating trainers
dex['teachable_moves'].remove('SUNNY_DAY')
dex['teachable_moves'].remove('RAIN_DANCE')
dex['teachable_moves'].remove('HAIL')
dex['teachable_moves'].remove('SANDSTORM')
dex['teachable_moves'].remove('DREAM_EATER')
dex['teachable_moves'].remove('SAFEGUARD')
dex['teachable_moves'].remove('SKILL_SWAP')
dex['teachable_moves'].remove('TORMENT')
dex['teachable_moves'].remove('RETURN')
dex['teachable_moves'].remove('FRUSTRATION')
dex['teachable_moves'].remove('SECRET_POWER')
dex['teachable_moves'].remove('ATTRACT')
dex['teachable_moves'].remove('PROTECT')
dex['teachable_moves'].remove('MIMIC')
dex['teachable_moves'].remove('SNATCH')
dex['teachable_moves'].remove('HIDDEN_POWER')

generate_rival_teams()

# hack: make enemies able to use starters even though they don't spawn in the wild
for starter in [ 'BULBASAUR', 'IVYSAUR', 'VENUSAUR', 'CHARMANDER', 'CHARMELEON', 'CHARIZARD', 'SQUIRTLE', 'WARTORTLE', 'BLASTOISE' ]:
    sdata = dex['base_stats.h'][starter]
    dex['encounter_data'][starter] = {
        'types' : [sdata['type1'], sdata['type2']],
        'egg_groups' : [sdata['eggGroup1'], sdata['eggGroup2']],
        'bst' : (sdata['baseHP'] + sdata['baseAttack'] + sdata['baseDefense'] + sdata['baseSpeed'] + sdata['baseSpAttack'] + sdata['baseSpDefense'])
    }

generate_trainers()
