#!/usr/bin/python3

import re
import json
import sys
import random
from enum import Enum, auto
from collections import defaultdict, OrderedDict

if(len(sys.argv) != 2):
    print('usage: replace_files.py [path to game decomp folder]')
    exit()

class GameVersion(Enum):
    FIRERED = 'pokefirered'
    RUBY = 'pokeruby'

decomp_folder = sys.argv[1]
version = GameVersion(re.compile(r'.*?/?([a-z]+)/?$').fullmatch(sys.argv[1].strip()).group(1))

class MonContext(Enum):
    UNKNOWN = auto()
    WILD = auto()
    TRAINER = auto()
    BOSS = auto()

with open('dex.json') as f:
    dex = json.load(f, object_pairs_hook=OrderedDict)

def generate_species_h():
    with open(f'templates/{version.value}/species.h_template') as f:
        template = f.read()
    
    ndex_list = '\n'.join(f'#define NATIONAL_DEX_{pk} {i}' for i, pk in enumerate(dex['national_dex']))
    
    hdex_list = '\n'.join(f'#define HOENN_DEX_{pk} {i}' for i, pk in enumerate(dex['hoenn_dex']))
    
    template = template.replace('[!NATIONAL_DEX_ORDER!]', ndex_list)
    template = template.replace('[!HOENN_DEX_ORDER!]', hdex_list)
    
    with open(decomp_folder + '/include/constants/species.h', 'w') as f:
        f.write(template)
    
    print('wrote /include/constants/species.h')
    
    # ruby only: replace pokemon_1.c where hoenn dex order is defined
    if version == GameVersion.RUBY:
        with open('templates/pokeruby/pokemon_1.c_template') as f:
            tmp = f.read()
            content = ',\n'.join([ 'NATIONAL_DEX_' + poke for poke in dex['hoenn_dex'][1:] ]) + ','
            tmp = tmp.replace('[[!CONTENT!]]', content)
        
        with open(decomp_folder + 'src/pokemon_1.c', 'w') as f:
            f.write(tmp)
        print('wrote /src/pokemon_1.c')
        

def generate_base_stats_h():
    with open(f'templates/{version.value}/base_stats.h_template') as f:
        template = f.read()
        
    poke_start = re.compile(r'\s\s\s\s\[SPECIES_(.+)\]\s=')
    poke_end = re.compile(r'\s\s\s\s\},')
    
    data = dex['base_stats.h']
    
    current_poke = None
    
    output = []
    
    for line in template.split('\n'):
        m = poke_start.search(line)
        
        if m != None and m.group(1) in data:
            current_poke = m.group(1)
            pkmn = data[current_poke]
            
            if pkmn == 'OLD_UNOWN':
                output.append(line)
            else:
                output.append(line)
                output.append('    {')
                
                if version == GameVersion.FIRERED:
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
                elif version == GameVersion.RUBY:
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
            .ability1 = ABILITY_{pkmn['abilities'][0]},
            .ability2 = ABILITY_{pkmn['abilities'][1]},
            .safariZoneFleeRate = {pkmn['safariZoneFleeRate']},
            .bodyColor = BODY_COLOR_{pkmn['bodyColor']},
            .noFlip = TRUE,""")
        
        if poke_end.search(line) != None:
            current_poke = None
        
        if current_poke == None:
            output.append(line)
    
    with open(decomp_folder + '/src/data/pokemon/base_stats.h', 'w') as f:
        f.write('\n'.join(output))
    
    print('wrote /src/data/pokemon/base_stats.h')

def generate_names_h_pokefirered():
    with open('templates/pokefirered/species_names.h_template') as f:
        template = f.read()
    
    names = dex['species_names.h']
    names.insert(0, '??????????')
    is_name = re.compile(r'\s\s\s\s_\("(.+)"\)')
    
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
    
    with open(decomp_folder + '/src/data/text/species_names.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/text/species_names.h')

def generate_names_h_pokeruby():
    with open('templates/pokeruby/species_names_en.h_template') as f:
        template = f.read()
    
    names = dex['species_names.h']
    names.insert(0, '??????????')
    is_name = re.compile(r'_\(.+\)')
    
    output = []
    
    index = 0
    
    for line in template.split('\n'):
        if is_name.search(line) != None:
            line = re.sub(is_name, f'_("{names[index]}")', line)
            index += 1
        output.append(line)
    
    with open(decomp_folder + '/src/data/text/species_names_en.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/text/species_names_en.h')

generate_names_h = {
    GameVersion.FIRERED : generate_names_h_pokefirered,
    GameVersion.RUBY : generate_names_h_pokeruby
}

def generate_pokemon_h():
    with open(f'templates/{version.value}/pokemon.h_template') as f:
        template = f.read()
    
    with open('templates/palette_template') as f:
        palette_template = f.read()
    
    if version == GameVersion.FIRERED:
        get_front_pic = re.compile(r'const\su32\s(.+)\s=\sINCBIN_U32\("graphics\/pokemon\/(.+)\/front.4bpp.lz"\);')
        get_back_pic = re.compile(r'const\su32\s(.+)\s=\sINCBIN_U32\("graphics\/pokemon\/(.+)\/back.4bpp.lz"\);')
        get_icon = re.compile(r'const\su8\s(.+)\s=\sINCBIN_U8\("graphics\/pokemon\/(.+)\/icon.4bpp"\);')
        get_palette = re.compile(r'const\su32\s.+\s=\sINCBIN_U32\(\"(.+)normal\.gbapal\.lz"\);')
    elif version == GameVersion.RUBY:
        get_front_pic = re.compile(r'const\su8\s(.+)\s=\sINCBIN_U8\("graphics\/pokemon\/(.+)\/front.4bpp.lz"\);')
        get_back_pic = re.compile(r'const\su8\s(.+)\s=\sINCBIN_U8\("graphics\/pokemon\/(.+)\/back.4bpp.lz"\);')
        get_icon = re.compile(r'const\su8\s(.+)\s=\sINCBIN_U8\("graphics\/pokemon\/(.+)\/icon.4bpp"\);')
        get_palette = re.compile(r'const\su8\s.+\s=\sINCBIN_U8\(\"(.+)normal\.gbapal\.lz"\);')

    
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
        
        if m_palette != None and index <= len(colors):
            palette_file = f'{decomp_folder}{m_palette.group(1)}normal.pal'
            
            while colors[index-1] == 'OLD_UNOWN':
                index = index+1
            
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
            if 'Deoxys' in m_front.group(1) and version == GameVersion.FIRERED: # TODO hack, deoxys needs a special sprite file, should make one
                output.append(line)
            else:
                if version == GameVersion.FIRERED:
                    output.append(f'const u32 {m_front.group(1)} = INCBIN_U32("graphics/pokemon/question_mark/circled/front.4bpp.lz");')
                elif version == GameVersion.RUBY:
                    output.append(f'const u8 {m_front.group(1)} = INCBIN_U8("graphics/pokemon/circled_question_mark/front.4bpp.lz");')
        elif m_back != None:
            if 'Deoxys' in m_back.group(1) and version == GameVersion.FIRERED:
                output.append(line)
            else:
                if version == GameVersion.FIRERED:
                    output.append(f'const u32 {m_back.group(1)} = INCBIN_U32("graphics/pokemon/question_mark/circled/back.4bpp.lz");')
                elif version == GameVersion.RUBY:
                    output.append(f'const u8 {m_back.group(1)} = INCBIN_U8("graphics/pokemon/circled_question_mark/back.4bpp.lz");')
        elif m_icon != None:
            output.append(f'const u8 {m_icon.group(1)} = INCBIN_U8("graphics/pokemon/question_mark/icon.4bpp");')
        else:
            output.append(line)
    with open(decomp_folder + '/src/data/graphics/pokemon.h', 'w') as f:
        f.write('\n'.join(output))
    
    print('wrote /src/data/graphics/pokemon.h')

def generate_egg_moves_h():
    with open(f'templates/{version.value}/egg_moves.h_template') as f:
        template = f.read()
    
    data = dex['egg_moves.h']
    output = []
    is_start = re.compile(r'\s\s\s\segg_moves\((.+),')
    
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        if len(data[poke]) != 0:
            movelist = ', '.join([ '\n              MOVE_'+mv for mv in data[poke] ])
            output.append(f'    egg_moves({poke}, {movelist}),\n')
    
    output.append(tmpl_end)
    
    with open(decomp_folder + '/src/data/pokemon/egg_moves.h', 'w') as f:
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
    
    with open(f'templates/{version.value}/tmhm_learnsets.h_template') as f:
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
    
    with open(decomp_folder + 'src/data/pokemon/tmhm_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/tmhm_learnsets.h')

def generate_tutor_learnsets_h_pokefirered():
    with open(f'templates/{version.value}/tutor_learnsets.h_template') as f:
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
    
    with open(decomp_folder + 'src/data/pokemon/tutor_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/tutor_learnsets.h')

generate_tutor_learnsets_h = {
    GameVersion.FIRERED : generate_tutor_learnsets_h_pokefirered,
    GameVersion.RUBY : lambda: None
}

def generate_pokedex_entries_h():
    with open('templates/pokefirered/pokedex_entries.h_template') as f:
        template = f.read()
    
    description_to_entry = {}
    
    species_def = re.compile(r'DEX_(.+)\]')
    get_description = re.compile('=\\s(.+?),')
    
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
                output.append(f"        .weight = {min(dex['pokedex_entries.h'][current_species]['weight'], 9999)},")
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
            
            if 'description' in line:
                description_to_entry[get_description.search(line).group(1)] = dex['pokedex_text_fr.h'][current_species]
        
        output.append(line)
    
    with open(decomp_folder + 'src/data/pokemon/pokedex_entries.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/pokedex_entries.h')
    
    return description_to_entry

def split_dex_entry(entry):
    lines = []
    
    i = 0
    while i < len(entry):
        if i >= 27 and entry[i] == ' ':
            lines.append(entry[:i])
            entry = entry[i+1:]
            i = 0
        i = i + 1
    
    if entry != "":
        lines.append(entry)
    
    if len(lines) > 3:
        print('Overlong pokedex entry:', lines)
    
    lb = "\\n"
    lines = [f'"{line + lb}"' for line in lines ]
    lines[-1] = lines[-1].replace('\\n', '')
    return '\n\t'.join(lines)
    

def generate_pokedex_text_fr_h(description_to_entry):
    with open('templates/pokefirered/pokedex_text_fr.h_template') as f:
        template = f.read()
    
    entries = dex['pokedex_text_fr.h']
    
    valid_line = re.compile('const\\su8\\s(.+?)\\[\\]\\s=\\s_\\($')
    valid_unused_line = re.compile('const\\su8\\s.+?\\[\\]\\s=\\s_\\(""\\);')
    
    lines = []
    
    for line in template.split('\n'):
        is_valid = valid_line.search(line)
        if is_valid != None:
            if 'Dummy' in line:
                lines.append(line + '"");')
            else:
                desc = is_valid.group(1)
                entry = description_to_entry[desc]
                lines.append(f'const u8 {desc}[] = _(\n\t{split_dex_entry(entry)});')
        elif valid_unused_line.search(line) != None:
            lines.append(line)
    
    output = '\n\n'.join(lines)
    
    with open(decomp_folder + 'src/data/pokemon/pokedex_text_fr.h', 'w') as f:
        f.write(output)
    print('wrote /src/data/pokemon/pokedex_text_fr.h')

def generate_pokedex_pokefirered():
    description_to_entry = generate_pokedex_entries_h()
    generate_pokedex_text_fr_h(description_to_entry)

def generate_pokedex_pokeruby():
    with open('templates/pokeruby/pokedex_entries_en.h_template') as f:
        template = f.read()
    
    desc_line_1 = re.compile(r'_1\[\]\s=\s_\(\n.+\n.+\n?.+\);')
    desc_line_2 = re.compile(r'_2\[\]\s=\s_\(\n.+\n.+\n?.+\);')
    
    desc_1_empty = """_1[] = _(
  "This is a newly discovered POKéMON.\\n"
  "It is currently under investigation.");"""
    
    desc_2_empty = """_2[] = _(
  "No detailed information is available\\n"
  "at this time.");"""
    
    template = re.sub(desc_line_1, lambda _: desc_1_empty, template)
    template = re.sub(desc_line_2, lambda _: desc_2_empty, template)
    
    dex_data = dex['pokedex_entries.h']
    pokelist = list(dex['national_dex'])
    
    output = []
    index = -1
    
    for line in template.split('\n'):
        
        if '{  //' in line:
            index += 1
        
        pokeid = pokelist[index]
        
        if index >= 0 and '.height' in line:
            height = 0
            
            if pokeid != 'NONE':
                height = dex_data[pokeid]['height']
            
            output.append(f"        .height = {height},")
        elif index >= 0 and '.weight' in line:
            weight = 0
            
            if pokeid != 'NONE':
                weight = dex_data[pokeid]['weight']
            
            output.append(f"        .weight = {min(weight, 9999)},")
        elif index >= 0 and '.categoryName' in line:
            cat_name = 'UNKNOWN'
            
            if pokeid != 'NONE':
                cat_name = dex_data[pokeid]['categoryName']
            
            output.append(f'        .categoryName = _("{cat_name}"),')
        elif '.pokemonScale' in line:
            output.append('        .pokemonScale = 256,')
        elif '.pokemonOffset' in line:
            output.append('        .pokemonOffset = 0,')
        elif '.trainerScale' in line:
            output.append('        .trainerScale = 256,')
        elif '.trainerOffset' in line:
            output.append('        .trainerOffset = 0,')
        else:
            output.append(line)
    
    with open(decomp_folder + 'src/data/pokedex_entries_en.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokedex_entries_en.h')

generate_pokedex = {
    GameVersion.FIRERED : generate_pokedex_pokefirered,
    GameVersion.RUBY : generate_pokedex_pokeruby
}

def evo_string(evo):
    if evo[0] == 'EVO_LEVEL':
        return f'{{EVO_LEVEL, {evo[1]}, SPECIES_{evo[2]}}}'
    if evo[0] == 'EVO_ITEM':
        return f'{{EVO_ITEM, ITEM_{evo[1]}, SPECIES_{evo[2]}}}'
    if evo[0] == 'EVO_FRIENDSHIP':
        return f'{{EVO_FRIENDSHIP, 0, SPECIES_{evo[2]}}}'
    
def generate_evolution_h():
    with open(f'templates/{version.value}/evolution.h_template') as f:
        template = f.read()
    
    data = dex['evolution.h']
    output = []
    tmpl_start, tmpl_end = template.split('[!CONTENT!]')
    
    output.append(tmpl_start)
    
    for poke in data.keys():
        value = '{' + ', '.join([ (evo_string(evo)) for evo in data[poke] ]) + '}'
        output.append(f'    [SPECIES_{poke}]  = {value},\n')
    
    output.append(tmpl_end)
    
    with open(decomp_folder + 'src/data/pokemon/evolution.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/evolution.h')

def generate_level_up_learnsets_h():
    with open(f'templates/{version.value}/level_up_learnsets.h_template') as f:
        template = f.read()
    
    if version == GameVersion.FIRERED:
        poke_start = re.compile(r'static\sconst\su16\s(.+)\[\]')
    elif version == GameVersion.RUBY:
        poke_start = re.compile(r'const\su16\s(.+)\[\]')
    
    output = []
    data = dex['level_up_learnsets.h']
    current_poke = None
    
    for line in template.split('\n'):
        m = poke_start.search(line)
        
        if line == '};':
            current_poke = None
        elif m != None:
            current_poke = m.group(1)
            moves_id = m.group(1)
            
            if version == GameVersion.RUBY:
                moves_id = 's' + moves_id[1:]
            
            if moves_id in data:
                if version == GameVersion.FIRERED:
                    output.append(f'static const u16 {current_poke}[] = {{')
                elif version == GameVersion.RUBY:
                    output.append(f'const u16 {current_poke}[] = {{')
                
                for mv in data[moves_id]:
                    output.append(f'    LEVEL_UP_MOVE({mv[0]}, MOVE_{mv[1]}),')
                output.append('    LEVEL_UP_END')
        
        if current_poke == None or (not moves_id in data):
            output.append(line)
        
    with open(decomp_folder + 'src/data/pokemon/level_up_learnsets.h', 'w') as f:
        f.write('\n'.join(output))
    print('wrote /src/data/pokemon/level_up_learnsets.h')

def generate_sprite_position_files_pokefirered():
    with open(decomp_folder + 'src/data/pokemon_graphics/enemy_mon_elevation.h', 'w') as f:
        with open('templates/pokefirered/enemy_mon_elevation.h_template') as t:
            f.write(t.read())
    print('wrote /src/data/pokemon_graphics/enemy_mon_elevation.h')
    
    with open(decomp_folder + 'src/data/pokemon_graphics/back_pic_coordinates.h', 'w') as f:
        with open('templates/pokefirered/back_pic_coordinates.h_template') as t:
            f.write(t.read())
    print('wrote /src/data/pokemon_graphics/back_pic_coordinates.h.h')
    
    with open(decomp_folder + 'src/data/pokemon_graphics/front_pic_coordinates.h', 'w') as f:
        with open('templates/pokefirered/front_pic_coordinates.h_template') as t:
            f.write(t.read())
    print('wrote /src/data/pokemon_graphics/front_pic_coordinates.h')

def generate_sprite_position_files_pokeruby():
    with open(decomp_folder + 'src/battle/battle_1.c', 'w') as f:
        with open('templates/pokeruby/battle_1.c_template') as t:
            f.write(t.read())
    print('wrote /src/battle/battle_1.c') 
    
    with open(decomp_folder + 'data/graphics/pokemon/front_pic_coords.inc', 'w') as f:
        with open('templates/pokeruby/front_pic_coords.inc_template') as t:
            f.write(t.read())
    print('wrote /data/graphics/pokemon/front_pic_coords.inc') 
    
    with open(decomp_folder + 'data/graphics/pokemon/back_pic_coords.inc', 'w') as f:
        with open('templates/pokeruby/back_pic_coords.inc_template') as t:
            f.write(t.read())
    print('wrote /data/graphics/pokemon/back_pic_coords.inc') 

generate_sprite_position_files = {
    GameVersion.FIRERED : generate_sprite_position_files_pokefirered,
    GameVersion.RUBY : generate_sprite_position_files_pokeruby
}

def filter_mons(mons, of_types, of_egg_groups, max_lvl, ctxt=MonContext.UNKNOWN, rarity_max_lvl=50):
    choices = []
    if len(mons) == 0:
        raise BaseException('no mons given')
    
    if of_types == None and of_egg_groups == None:
        choices.extend(mons)
    else:
        for poke_name in mons:
            poke = dex['encounter_data'][poke_name]
            if poke['types'][0] in of_types or poke['types'][1] in of_types or poke['egg_groups'][0] in of_egg_groups or poke['egg_groups'][1] in of_egg_groups:
                choices.append(poke_name)
    
    choices.sort(key=lambda pk: dex['encounter_data'][pk]['bst'])
    
    rarity = max_lvl/rarity_max_lvl
    target_len = int(len(choices) * rarity)
    rand_max = random.randint(2,4)
    if target_len < rand_max:
        target_len = rand_max
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

assigned_mons = set()

def assign_wild_mons(mons, wild_mons):
    max_lvl = max([ mon['max_level'] for mon in wild_mons['mons'] ])
    
    mons = filter_mons(mons, None, None, max_lvl, rarity_max_lvl = 50 if version == GameVersion.FIRERED else 40)

    for mon in wild_mons['mons']:
        chosen = adjust_evo(random.choice(mons), mon['min_level'], mon['max_level'], ctxt=MonContext.WILD)
        
        assigned_mons.add(base_form(chosen))
        mon['species'] = 'SPECIES_' + chosen

map_cache = {}

def get_map_data(map_name, enc_data):
    data = None
    map_id = None
    for key in enc_data.keys():
        if map_name == key:
            data = enc_data[key]
            map_id = map_name
            break
        elif key[-1] == '*' and key[0:len(key)-1] == map_name[0:len(key)-1]:
            data = enc_data[key]
            map_id = key
    return (data, map_id)

def set_map_data(map_name, encounters, enc_data, mon_list):
    data, map_id = get_map_data(map_name, enc_data)
    
    if data == None:
        print('!!!! cant find data:', map_name)
        return
    
    if not map_id.startswith('SPECIAL') and not ('habitats' in data and 'motifs' in data):
        print('!!!!! incomplete data:', map_name, dict(data))
    
    is_post = 'postgame' in data and data['postgame']
    mons = mon_list['post'] if is_post else mon_list['main']
    map_id = map_id + ('_post' if is_post else '')
    
    if map_id not in map_cache:
        map_cache[map_id] = generate_mons(mons, data['habitats'], data['types'] if 'types' in data else [], data['not_types'] if 'not_types' in data else [], data['motifs'] if 'motifs' in data else [])
    
    try:
        assign_wild_mons(map_cache[map_id], encounters)
    except BaseException as e:
        print(f'cannot assign wild mons for {map_name} {dict(data)}')
        print('available:', map_cache[map_id])
        raise e
    
    if map_name == 'MAP_ROUTE101' and version == GameVersion.RUBY:
        global ROUTE101_WILD_POOCHYENA
        ROUTE101_WILD_POOCHYENA = encounters['mons'][0]['species']

def generate_mons(mons, habitats, types, not_types, motifs):
    mons = list(mons)
    random.shuffle(mons)
    
    mon_values = {}
    for m in mons:
        mon_values[m] = wild_mon_value(m, habitats, types, not_types, motifs)
    mons[:] = [m for m in mons if mon_values[m] > 0]
    
    mons.sort(key=lambda m: -mon_values[m])
    
    target_len = 10# max(10, len(mons)//2)
    return mons[0:min(target_len, len(mons))]

def wild_mon_value(mon, habitats, types, not_types, motifs):
    val = 0
    mon_habitats = dex['encounter_data'][mon]['habitats']
    mon_motifs = dex['encounter_data'][mon]['motifs']
    mon_types = set(dex['encounter_data'][mon]['types'])
    
    any_habitat = False
    for h in habitats:
        if h in mon_habitats:
            val += 1
            any_habitat = True
    
    if not any_habitat:
        val = val - 100000
    
    for m in motifs:
        if m in mon_motifs:
            val += 5
    
    for t in types:
        if t in mon_types:
            val += 10
    
    for t in not_types:
        if t in mon_types:
            val -= 30
    
    if mon not in assigned_mons:
        val += 5
    
    # TODO adjust for already encountered
    return val

def try_generate_wild_encounters(mon_list):
    with open(f'templates/{version.value}/wild_encounters.json_template') as f:
        encs = json.load(f)
    
    with open(f'encounter_data_{version.value}.json') as f:
        enc_data = json.load(f, object_pairs_hook=OrderedDict)
        enc_data_order = list(enc_data.keys())
    
    entry_order = []
    entries = {}
    entry_sort_value = {}
    for entry in encs['wild_encounter_groups'][0]['encounters']:
        if (not 'LeafGreen' in entry['base_label']) and (not 'Sapphire' in entry['base_label']):
            if entry['map'] == 'MAP_SIX_ISLAND_ALTERING_CAVE':
                if entry['base_label'] != 'sSixIslandAlteringCave_FireRed':
                    continue
            
            entry_order.append(entry['map'])
            entries[entry['map']] = entry
            data, map_id = get_map_data(entry['map'], enc_data)
            entry_sort_value[entry['map']] = enc_data_order.index(map_id) if map_id in enc_data_order else 0
    
    entry_order.sort(key=lambda map_id: entry_sort_value[map_id])
    
    for entry_id in entry_order:
        entry = entries[entry_id]
        if 'LeafGreen' in entry['base_label'] or 'Sapphire' in entry['base_label']:
            continue
        
        map_name = entry['map']
        data, map_id = get_map_data(map_name, enc_data)
        
        if 'land_mons' in entry:
            set_map_data(entry['map'], entry['land_mons'], enc_data, mon_list)
        
        if 'water_mons' in entry:
            if data is None or 'surfing' not in data:
                print('!!!!!! surfing not declared in', map_name)
            else:
                if 'postgame' in data and data['postgame']:
                    enc_data[data['surfing']]['postgame'] = True
                else:
                    enc_data[data['surfing']]['postgame'] = False
                set_map_data(data['surfing'], entry['water_mons'], enc_data, mon_list)
        
        if 'fishing_mons' in entry:
            if data is None or 'fishing' not in data:
                print('!!!!!! fishing not declared in', map_name)
            else:
                if 'postgame' in data and data['postgame']:
                    enc_data[data['fishing']]['postgame'] = True
                else:
                    enc_data[data['fishing']]['postgame'] = False
                set_map_data(data['fishing'], entry['fishing_mons'], enc_data, mon_list)
        
        if 'rock_smash_mons' in entry:
            if data is None or 'rock_smash' not in data:
                print('!!!!!! rock smash not declared in', map_name)
            else:
                if 'postgame' in data and data['postgame']:
                    enc_data[data['rock_smash']]['postgame'] = True
                else:
                    enc_data[data['rock_smash']]['postgame'] = False
                set_map_data(data['rock_smash'], entry['rock_smash_mons'], enc_data, mon_list)
    
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

def generate_wild_encounters(mon_list):
    encs = try_generate_wild_encounters(mon_list)
    
    main_families = list(mon_list['main'])
    post_families = list(mon_list['post'])
    main_missing = list(main_families)
    post_missing = list(set(post_families).difference(main_families))
    
    for mon in assigned_mons:
        if mon in post_missing:
            post_missing.remove(mon)
        if mon in main_missing:
            main_missing.remove(mon)
    
    print('unavailable families:', main_missing, post_missing)
    
    if version == GameVersion.FIRERED:
        generate_in_game_pokemon_pokefirered(main_families, post_families, main_missing, post_missing)
    elif version == GameVersion.RUBY:
        generate_in_game_pokemon_pokeruby(main_families, main_missing)
    
    print('final unavailable families:', main_missing, post_missing)
    
    with open(decomp_folder + 'src/data/wild_encounters.json', 'w') as f:
        f.write(json.dumps(encs, indent=2, sort_keys=False))

def generate_in_game_pokemon_pokefirered(main_families, post_families, main_missing, post_missing):
    # replace lapras gift
    with open(decomp_folder + 'data/maps/SilphCo_7F/scripts.inc', 'w') as f:
        with open('templates/pokefirered/SilphCo_7F_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_LAPRAS', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
        f.write(tmp)
        print('wrote /data/maps/SilphCo_7F/scripts.inc')
    
    # replace eevee gift
    with open(decomp_folder + 'data/maps/CeladonCity_Condominiums_RoofRoom/scripts.inc', 'w') as f:
        with open('templates/pokefirered/CeladonCity_Condominiums_RoofRoom_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_EEVEE', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
        f.write(tmp)
        print('wrote /data/maps/CeladonCity_Condominiums_RoofRoom/scripts.inc')
    
    # replace magikarp gift
    with open(decomp_folder + 'data/maps/Route4_PokemonCenter_1F/scripts.inc', 'w') as f:
        with open('templates/pokefirered/Route4_PokemonCenter_1F_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_MAGIKARP', 'SPECIES_'+pick_rare_pkmn([], main_families))
        f.write(tmp)
        print('wrote /data/maps/Route4_PokemonCenter_1F/scripts.inc')
    
    # replace hitmon gift
    with open(decomp_folder + 'data/maps/SaffronCity_Dojo/scripts.inc', 'w') as f:
        with open('templates/pokefirered/SaffronCity_Dojo_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_HITMONCHAN', 'SPECIES_'+pick_rare_pkmn([], main_families, req_type='FIGHTING'))
            tmp = tmp.replace('SPECIES_HITMONLEE', 'SPECIES_'+pick_rare_pkmn([], main_families, req_type='FIGHTING'))
        f.write(tmp)
        print('wrote /data/maps/SaffronCity_Dojo/scripts.inc')
    
    # replace hypno encounter
    with open(decomp_folder + 'data/maps/ThreeIsland_BerryForest/scripts.inc', 'w') as f:
        with open('templates/pokefirered/ThreeIsland_BerryForest_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_HYPNO', 'SPECIES_'+adjust_evo(pick_rare_pkmn([], main_families, req_type='PSYCHIC'), 30))
        f.write(tmp)
        print('wrote /data/maps/ThreeIsland_BerryForest/scripts.inc')
    
    # replace togepi egg gift
    with open(decomp_folder + 'data/maps/FiveIsland_WaterLabyrinth/scripts.inc', 'w') as f:
        with open('templates/pokefirered/FiveIsland_WaterLabyrinth_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_TOGEPI', 'SPECIES_'+pick_rare_pkmn(post_missing, post_families))
        f.write(tmp)
        print('wrote /data/maps/FiveIsland_WaterLabyrinth/scripts.inc')
    
    # change roamer to mew
    with open(decomp_folder + 'src/roamer.c', 'w') as f:
        with open('templates/pokefirered/roamer.c_template') as t:
            tmp = t.read().replace('SPECIES_ENTEI', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_RAIKOU', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_SUICUNE', 'SPECIES_MEW')
        f.write(tmp)
        print('wrote /src/roamer.c')
    
    # change roamer visible in pokedex
    with open(decomp_folder + 'src/wild_pokemon_area.c', 'w') as f:
        with open ('templates/pokefirered/wild_pokemon_area.c_template') as t:
            tmp = t.read().replace('SPECIES_ENTEI', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_RAIKOU', 'SPECIES_MEW')
            tmp = tmp.replace('SPECIES_SUICUNE', 'SPECIES_MEW')
        f.write(tmp)
        print('wrote /src/wild/pokemon/area.c')
    
    # replace game corner prizes
    with open(decomp_folder + 'data/maps/CeladonCity_GameCorner_PrizeRoom/scripts.inc', 'w') as f:
        with open('templates/pokefirered/CeladonCity_GameCorner_PrizeRoom_scripts.inc_template') as t:
            tmp = t.read()
            
            tmp = tmp.replace('SPECIES_ABRA', '[[$1$]]')
            tmp = tmp.replace('SPECIES_CLEFAIRY', '[[$2$]]')
            tmp = tmp.replace('SPECIES_SCYTHER', '[[$3$]]')
            tmp = tmp.replace('SPECIES_PINSIR', '[[$3$]]')
            tmp = tmp.replace('SPECIES_DRATINI', '[[$4$]]')
            tmp = tmp.replace('SPECIES_PORYGON', '[[$5$]]')
            
            tmp = tmp.replace('[[$1$]]', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
            tmp = tmp.replace('[[$2$]]', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
            tmp = tmp.replace('[[$3$]]', 'SPECIES_SQUIRTLE')
            tmp = tmp.replace('[[$4$]]', 'SPECIES_CHARMANDER')
            tmp = tmp.replace('[[$5$]]', 'SPECIES_BULBASAUR')
        f.write(tmp)
        print('wrote /data/maps/CeladonCity_GameCorner_PrizeRoom/scripts.inc')
    
    # replace in-game trades
    get_trade_species = re.compile(r'\s+\.species\s=\s(.+),')
    get_wanted_species = re.compile(r'\s+\.requestedSpecies\s=\s(.+)')
    trades_h_out = []
    with open('templates/pokefirered/ingame_trades.h_template') as f:
        for line in f.read().split('\n'):
            m_trade = get_trade_species.search(line)
            m_wanted = get_wanted_species.search(line)
            if m_trade != None:
                unav = main_missing
                if 'NIDO' in m_trade.group(1):
                    unav = []
                trades_h_out.append(f'        .species = SPECIES_{pick_rare_pkmn(main_missing, main_families)},')
            elif m_wanted != None:
                trades_h_out.append(f'        .requestedSpecies = SPECIES_{pick_rare_pkmn([], main_families)}')
            else:
                trades_h_out.append(line)
    
    with open(decomp_folder + 'src/data/ingame_trades.h', 'w') as f:
        f.write('\n'.join(trades_h_out))
    print('wrote /src/data/ingame_trades.h')

def generate_in_game_pokemon_pokeruby(main_families, main_missing):
    # replace wynaut gift
    with open(decomp_folder + 'data/maps/LavaridgeTown/scripts.inc', 'w') as f:
        with open('templates/pokeruby/LavaridgeTown_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_WYNAUT', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
        f.write(tmp)
        print('wrote /data/maps/LavaridgeTown/scripts.inc')
    
    # replace castform gift
    with open(decomp_folder + 'data/maps/Route119_WeatherInstitute_2F/scripts.inc', 'w') as f:
        with open('templates/pokeruby/Route119_WeatherInstitute_2F_scripts.inc') as t:
            tmp = t.read().replace('SPECIES_CASTFORM', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
        f.write(tmp)
        print('wrote /data/maps/Route119_WeatherInstitute_2F/scripts.inc')
    
    # replace kecleon & electrode encounters
    kecleon = 'SPECIES_'+pick_rare_pkmn(main_missing, main_families)
    electrode = 'SPECIES_'+pick_rare_pkmn(main_missing, main_families)
    with open(decomp_folder + 'data/scripts/static_pokemon.inc', 'w') as f:
        with open('templates/pokeruby/static_pokemon.inc_template') as t:
            tmp = t.read().replace('[[KECLEON]]', kecleon)
            tmp = tmp.replace('[[ELECTRODE]]', electrode)
        f.write(tmp)
        print('wrote /data/scripts/static_pokemon.inc')
    
    # kecleon fought with steven
    with open(decomp_folder + 'data/maps/Route120/scripts.inc', 'w') as f:
        with open('templates/pokeruby/Route120_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_KECLEON', kecleon)
        f.write(tmp)
        print('wrote /data/maps/Route120/scripts.inc')
    
    # replace in-game trades
    wanted1 = 'SPECIES_'+pick_rare_pkmn([], main_families)
    wanted2 = 'SPECIES_'+pick_rare_pkmn([], main_families)
    wanted3 = 'SPECIES_'+pick_rare_pkmn([], main_families)
    given1 = 'SPECIES_'+pick_rare_pkmn(main_missing, main_families)
    given2 = 'SPECIES_'+pick_rare_pkmn(main_missing, main_families)
    given3 = 'SPECIES_'+pick_rare_pkmn(main_missing, main_families)
    with open(decomp_folder + 'src/trade.c', 'w') as f:
        with open('templates/pokeruby/trade.c_template') as t:
            tmp = t.read().replace('[[WANTED_1]]', wanted1)
            tmp = tmp.replace('[[WANTED_2]]', wanted2)
            tmp = tmp.replace('[[WANTED_3]]', wanted3)
            tmp = tmp.replace('[[GIVEN_1]]', given1)
            tmp = tmp.replace('[[GIVEN_2]]', given2)
            tmp = tmp.replace('[[GIVEN_3]]', given3)
        f.write(tmp)
        print('wrote /src/trade.c')
    
    # replace beldum gift
    with open(decomp_folder + 'data/maps/MossdeepCity_StevensHouse/scripts.inc', 'w') as f:
        with open('templates/pokeruby/MossdeepCity_StevensHouse_scripts.inc_template') as t:
            tmp = t.read().replace('SPECIES_BELDUM', 'SPECIES_'+pick_rare_pkmn(main_missing, main_families))
        f.write(tmp)
        print('wrote /data/maps/MossdeepCity_StevensHouse/scripts.inc')
    
    # replace route 101 poochyena
    global ROUTE101_WILD_POOCHYENA
    with open(decomp_folder + 'src/battle_controllers.c', 'w') as f:
        with open('templates/pokeruby/battle_controllers.c_template') as t:
            tmp = t.read().replace('SPECIES_POOCHYENA', ROUTE101_WILD_POOCHYENA)
        f.write(tmp)
        print('wrote /src/battle_controllers.c')

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
    
    chosen = list(chosen)[0:4]
    
    # use signature move unless they have something better
    if signature_tm != None and dex['moves'][signature_tm]['damaging'] and not signature_tm in chosen:
        for index, move in enumerate(chosen):
            if dex['moves'][move]['damaging'] and dex['moves'][move]['type'] == dex['moves'][signature_tm]['type'] and dex['moves'][move]['value'] < dex['moves'][signature_tm]['value']:
                chosen[index] = signature_tm
                break
    
    # if not enough moves, fuck this, add random good ones
    if len(chosen) < 4:
        for ch in chosen:
            available.remove(ch)
        available = list(available)
        available.sort(key=by_move_value)
        
        while len(available) > 0 and len(chosen) < 4:
            random_move = available[-1]
            available.remove(random_move)
            chosen.append(random_move)
    
    while len(chosen) < 4:
        chosen = list(chosen)
        chosen.append('NONE')
    
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
    
    good_amount = min(len(nondamaging), max(3, int(len(nondamaging)/2)))
    
    nondamaging = nondamaging[good_amount-1:]
    
    # might not pick these because otherwise they're spammed everywhere
    #for ou in overused_nondmg_attacks:
    #    if ou in nondamaging and random.random() > 0.33:
    #        nondamaging.remove(ou)
    
    if len(nondamaging) == 0:
        return None
    return random.choice(nondamaging)

def generate_rival_teams_pokefirered(mon_list):
    global grass_team
    global fire_team
    global water_team
    bird = base_form(random.choice(filter_mons(mon_list, ['FLYING'], [], 10)))
    
    grass_mon = base_form(random.choice(filter_mons(mon_list, ['GRASS'], [], 50)))
    water_mon = base_form(random.choice(filter_mons(mon_list, ['WATER'], [], 50)))
    fire_mon = base_form(random.choice(filter_mons(mon_list, ['FIRE'], [], 50)))
    
    psy_mon = base_form(random.choice(filter_mons(mon_list, ['PSYCHIC'], [], 50)))
    rock_mon = base_form(random.choice(filter_mons(mon_list, ['ROCK'], [], 50)))
    
    grass_team = [ rock_mon, water_mon, fire_mon,  psy_mon, bird, 'BULBASAUR' ]
    fire_team =  [ rock_mon, grass_mon, water_mon, psy_mon, bird, 'CHARMANDER' ]
    water_team = [ rock_mon, fire_mon,  grass_mon, psy_mon, bird, 'SQUIRTLE' ]
    
    if len(grass_team) != len(set(grass_team)) or len(fire_team) != len(set(fire_team)) or len(water_team) != len(set(water_team)):
        generate_rival_teams_pokefirered(mon_list)

def generate_rival_teams_pokeruby(mon_list):
    global wally_team
    wally_team = []
    while len(wally_team) < 4:
        wally_team.append(base_form(random.choice(filter_mons(mon_list, None, None, 50))))
    wally_team.append('RALTS')
    
    global grass_team
    global fire_team
    global water_team
    
    bird = base_form(random.choice(filter_mons(mon_list, ['FLYING'], [], 50)))
    grass_mon = base_form(random.choice(filter_mons(mon_list, ['GRASS'], [], 30)))
    water_mon = base_form(random.choice(filter_mons(mon_list, ['WATER'], [], 30)))
    fire_mon = base_form(random.choice(filter_mons(mon_list, ['FIRE'], [], 30)))
    
    grass_team = [ bird, fire_mon, water_mon, 'TREECKO' ]
    water_team = [ bird, grass_mon, fire_mon, 'MUDKIP' ]
    fire_team =  [ bird, water_mon, grass_mon, 'TORCHIC' ]

def get_rival_team_terry(current_trainer, current_mon_count):
    global grass_team
    global fire_team
    global water_team
    
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
        return [ water_team[current_mon_count + offset] ]
    elif current_trainer['id'].endswith('Charmander'):
        return [ fire_team[current_mon_count + offset] ]
    elif current_trainer['id'].endswith('Bulbasaur'):
        return [ grass_team[current_mon_count + offset] ]

def get_rival_team_wally(current_trainer, current_mon_count):
    global wally_team
    
    if current_trainer['id'] == 'gTrainerParty_Wally2':
        return [ 'RALTS' ]
    else:
        return [ wally_team[current_mon_count] ]

def get_rival_team_brendanmay(current_trainer, current_mon_count):
    global grass_team
    global fire_team
    global water_team
    
    cid = current_trainer['id']
    
    if cid == 'gTrainerParty_Brendan1' or cid == 'gTrainerParty_May1':
        party = grass_team
        offset = 3
    elif cid == 'gTrainerParty_Brendan2' or cid == 'gTrainerParty_May2':
        party = grass_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan3' or cid == 'gTrainerParty_May3':
        party = grass_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan4' or cid == 'gTrainerParty_May4':
        party = fire_team
        offset = 3
    elif cid == 'gTrainerParty_Brendan5' or cid == 'gTrainerParty_May5':
        party = fire_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan6' or cid == 'gTrainerParty_May6':
        party = fire_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan7' or cid == 'gTrainerParty_May7':
        party = water_team
        offset = 3
    elif cid == 'gTrainerParty_Brendan8' or cid == 'gTrainerParty_May8':
        party = water_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan9' or cid == 'gTrainerParty_May9':
        party = water_team
        offset = 1
    elif cid == 'gTrainerParty_Brendan10' or cid == 'gTrainerParty_May10':
        party = grass_team
        offset = 0
    elif cid == 'gTrainerParty_Brendan11' or cid == 'gTrainerParty_May11':
        party = fire_team
        offset = 0
    elif cid == 'gTrainerParty_Brendan12' or cid == 'gTrainerParty_May12':
        party = water_team
        offset = 0
    
    return [ party[current_mon_count + offset] ]

defensive_items = [ 'ITEM_BRIGHT_POWDER', 'ITEM_FOCUS_BAND', 'ITEM_LEFTOVERS', 'ITEM_LUM_BERRY', 'ITEM_SITRUS_BERRY', 'ITEM_WHITE_HERB' ]
physical_offensive_items = [ 'ITEM_KINGS_ROCK', 'ITEM_QUICK_CLAW', 'ITEM_SALAC_BERRY', 'ITEM_SCOPE_LENS', 'ITEM_LIECHI_BERRY' ]
special_offensive_items = [ 'ITEM_KINGS_ROCK', 'ITEM_QUICK_CLAW', 'ITEM_SALAC_BERRY', 'ITEM_SCOPE_LENS', 'ITEM_PETAYA_BERRY' ]

type_items = {
    'FIGHTING' : 'ITEM_BLACK_BELT',
    'DARK' : 'ITEM_BLACK_GLASSES',
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

def generate_trainers(mon_lists):
    global grass_team
    global fire_team
    global water_team
    
    trainer_start = re.compile(r'\s+\[TRAINER_')
    get_name = re.compile(r'\s+\.trainerName\s=\s_\("(.+)"\),')
    if version == GameVersion.FIRERED:
        get_id = re.compile(r'(sTrainerMons_.+)}')
    else:
        get_id = re.compile(r'(gTrainerParty_.+)}')
    get_class = re.compile(r'\s+\.trainerClass\s=\s(.+),')
    
    trainer_data = {}
    
    with open(f'class_data_{version.value}.json') as f:
        class_data = json.load(f)
    
    trainers_h = 'src/data/trainers.h' if version == GameVersion.FIRERED else 'src/data/trainers_en.h'
    
    with open(decomp_folder + trainers_h) as f:
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
                trainer_id = m.group(1).strip()
                trainer_data[trainer_id] = { 'name' : name, 'class' : trainer_class, 'id' : trainer_id }
    
    with open(f'templates/{version.value}/trainer_parties.h_template') as f:
        parties_h = f.read()
    
    if version == GameVersion.FIRERED:
        party_start = re.compile(r'static\sconst\sstruct\s.+\s(sTrainerMons_.+)\[\]')
        party_lvl = re.compile(r'\s+\.lvl\s=\s(.+),')
        party_species = re.compile(r'\s+\.species\s=\s(.+),')
    else:
        party_start = re.compile(r'const\sstruct\s.+\s(gTrainerParty_.+)\[\]')
        party_lvl = re.compile(r'\s+\.level\s=\s(.+),')
        party_species = re.compile(r'\s+\.species\s=\s(.+),?')
    party_moves = re.compile(r'\s+\.moves\s=\s(.+),')
    party_item = re.compile(r'\s+.heldItem\s=\s(.+),')
    
    parties_h_out = []
    current_trainer = None
    current_level = None
    current_species = None
    current_mon_count = None
    dupes = set()
    rematch_team = [None, None, None, None, None, None]
    rematch_trainers = {}
    
    for line in parties_h.split('\n'):
        m = party_start.search(line)
        
        if m != None:
            
            # save previous rematch team
            if current_trainer != None:
                rematch_trainers[current_trainer['name']] = rematch_team
            
            if m.group(1) in trainer_data:
                current_trainer = trainer_data[m.group(1)]
                
                postgame = current_trainer['id'] in class_data['postgame_trainers']
                
                if postgame:
                    class_data['postgame_trainers'].remove(current_trainer['id'])
                
                mon_list = mon_lists['post'] if postgame else mon_lists['main']
            else:
                current_trainer = None
                current_level = None
                current_species = None
            
            if current_trainer != None and current_trainer['name'] != 'GRUNT' and current_trainer['name'] in rematch_trainers:
                rematch_team = rematch_trainers[current_trainer['name']]
            else:
                rematch_team = [None, None, None, None, None, None]
            current_mon_count = 0
            dupes.clear()
        
        m_sp = party_species.search(line)
        m_mv = party_moves.search(line)
        m_lvl = party_lvl.search(line)
        m_item = party_item.search(line)
        
        if m_sp != None and current_trainer != None:
            if current_trainer['class'] in class_data['special_classes']:
                if current_trainer['name'] in class_data['special_type_preference']:
                    typepref = class_data['special_type_preference'][current_trainer['name']]
                    if type(typepref) is list:
                        typepref = typepref[current_mon_count]
                    
                    mons = filter_mons(mon_list, typepref, [], current_level+15, ctxt=MonContext.BOSS)
                    #print('for', current_trainer['name'], mons, 'dupes:', dupes)
                    for mon in list(mons):
                        if base_form(mon) in dupes:
                            mons.remove(mon)
                            #print("won't dupe", mon)
                    if len(mons) == 0:
                        mons = filter_mons(mon_list, typepref, [], current_level+15, ctxt=MonContext.BOSS)
                
                elif current_trainer['name'] == 'TERRY':
                    mons = get_rival_team_terry(current_trainer, current_mon_count)
                
                elif current_trainer['name'] == 'WALLY':
                    mons = get_rival_team_wally(current_trainer, current_mon_count)
                
                elif current_trainer['name'] == 'BRENDAN' or current_trainer['name'] == 'MAY':
                    mons = get_rival_team_brendanmay(current_trainer, current_mon_count)
                        
            elif current_trainer['name'] in class_data['gym_trainers'].keys():
                gym_trainer_type = class_data['gym_trainers'][current_trainer['name']]
                mons = filter_mons(mon_list, gym_trainer_type, [], current_level)
                
            else:
                tr_class = class_data['classes'][current_trainer['class']]
                mons = filter_mons(mon_list, tr_class['types'], tr_class['egg_groups'], current_level)
            
            is_boss = current_trainer['class'] in class_data['special_classes']
            
            if rematch_team[current_mon_count] != None and not is_boss:
                mon = rematch_team[current_mon_count]
            else:
                mon = random.choice(mons)
                rematch_team[current_mon_count] = mon
            
            mon = adjust_evo(mon, current_level, ctxt=(MonContext.BOSS if is_boss else MonContext.TRAINER))
            
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
    
    if len(class_data['postgame_trainers']) != 0:
        print('!!! posttrainers not found:', class_data['postgame_trainers'])
    
    with open(decomp_folder + 'src/data/trainer_parties.h', 'w') as f:
        f.write('\n'.join(parties_h_out))
    print('wrote /src/data/trainer_parties.h')
    
generate_species_h()
generate_base_stats_h()
generate_names_h[version]()
generate_pokemon_h()
generate_egg_moves_h()
generate_tmhm_learnsets_h()
generate_tutor_learnsets_h[version]()
generate_pokedex[version]()
generate_evolution_h()
generate_level_up_learnsets_h()
generate_sprite_position_files[version]()

if version == GameVersion.FIRERED:
    mon_list = {
        'main' : dex['encounter_list_kanto'],
        'post' : dex['encounter_list_kanto_post']
    }
elif version == GameVersion.RUBY:
    mon_list = {
        'main' : dex['encounter_list_hoenn'],
        'post' : []
    }

basic_main = set()
for mon in mon_list['main']:
    basic_main.add(base_form(mon))

basic_post = set()
for mon in mon_list['post']:
    basic_post.add(base_form(mon))

if version == GameVersion.FIRERED:
    # allow gen 2 starters in wild
    basic_post.update([ 'CHIKORITA', 'CYNDAQUIL', 'TOTODILE' ])

generate_wild_encounters({ 'main' : basic_main, 'post' : basic_post })

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

if version == GameVersion.FIRERED:
    generate_rival_teams_pokefirered(mon_list['main'])
    
    # hack: make enemies able to use starters even though they don't spawn in the wild
    for starter in [ 'BULBASAUR', 'IVYSAUR', 'VENUSAUR', 'CHARMANDER', 'CHARMELEON', 'CHARIZARD', 'SQUIRTLE', 'WARTORTLE', 'BLASTOISE' ]:
        mon_list['main'].append(starter)
        mon_list['post'].append(starter)

    for starter in [ 'CHIKORITA', 'BAYLEEF', 'MEGANIUM', 'CYNDAQUIL', 'QUILAVA', 'TYPHLOSION', 'TOTODILE', 'CROCONAW', 'FERALIGATR' ]:
        mon_list['post'].append(starter)
elif version == GameVersion.RUBY:
    generate_rival_teams_pokeruby(mon_list['main'])
    
    for starter in [ 'TREECKO', 'GROVYLE', 'SCEPTILE', 'TORCHIC', 'COMBUSKEN', 'BLAZIKEN', 'MUDKIP', 'MARSHTOMP', 'SWAMPERT' ]:
        mon_list['main'].append(starter)

generate_trainers(mon_list)
