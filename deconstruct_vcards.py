#!/usr/bin/env python3
import os
import json
import re

VCF_PATH = "/Users/ricardo/Desktop/recovered_contacts.vcf"
JSON_OUTPUT_PATH = "/Users/ricardo/Desktop/deconstructed_contacts.json"

def unescape_vcf_value(val):
    if not val:
        return ""
    # Unescape backslash-escaped characters
    val = val.replace('\\\\', '\\').replace('\\;', ';').replace('\\,', ',')
    val = val.replace('\\n', '\n').replace('\\N', '\n')
    return val

def parse_params(params_list):
    params = {}
    for p in params_list:
        if '=' in p:
            k, v = p.split('=', 1)
            k = k.upper().strip()
            v = v.strip()
            params[k] = v
        else:
            # Standalone param, e.g. TYPE=WORK can sometimes be just WORK
            params[p.upper().strip()] = True
    return params

def parse_vcf(vcf_content):
    # Unfold lines (VCF lines folded with a leading space or tab)
    unfolded_lines = []
    for line in vcf_content.splitlines():
        if not line:
            continue
        if line[0] in (' ', '\t'):
            if unfolded_lines:
                unfolded_lines[-1] += line[1:]
        else:
            unfolded_lines.append(line)

    cards = []
    current_card = None

    for line in unfolded_lines:
        if line.startswith("BEGIN:VCARD"):
            current_card = {
                'uid': '',
                'formatted_name': '',
                'structured_name': {},
                'organization': '',
                'title': '',
                'note': '',
                'birthday': '',
                'telephones': [],
                'emails': [],
                'addresses': [],
                'urls': [],
                'social_profiles': [],
                'instant_messages': [],
                'revision': ''
            }
            continue
        elif line.startswith("END:VCARD"):
            if current_card:
                cards.append(current_card)
                current_card = None
            continue

        if not current_card:
            continue

        if ':' not in line:
            continue

        prop_part, val_part = line.split(':', 1)
        val_unescaped = unescape_vcf_value(val_part)

        # Parse property name and parameters
        parts = prop_part.split(';')
        prop_name = parts[0].upper().strip()
        params = parse_params(parts[1:])

        if prop_name == 'UID':
            current_card['uid'] = val_unescaped
        elif prop_name == 'FN':
            current_card['formatted_name'] = val_unescaped
        elif prop_name == 'N':
            # Structured Name: Family;Given;Additional;Prefix;Suffix
            n_parts = val_unescaped.split(';')
            while len(n_parts) < 5:
                n_parts.append('')
            current_card['structured_name'] = {
                'family': n_parts[0],
                'given': n_parts[1],
                'additional': n_parts[2],
                'prefix': n_parts[3],
                'suffix': n_parts[4]
            }
        elif prop_name == 'ORG':
            current_card['organization'] = val_unescaped
        elif prop_name == 'TITLE':
            current_card['title'] = val_unescaped
        elif prop_name == 'NOTE':
            current_card['note'] = val_unescaped
        elif prop_name == 'BDAY':
            current_card['birthday'] = val_unescaped
        elif prop_name == 'REV':
            current_card['revision'] = val_unescaped
        elif prop_name == 'TEL':
            tel_type = params.get('TYPE', 'OTHER')
            current_card['telephones'].append({
                'value': val_unescaped,
                'type': tel_type
            })
        elif prop_name == 'EMAIL':
            email_type = params.get('TYPE', 'OTHER')
            current_card['emails'].append({
                'value': val_unescaped,
                'type': email_type
            })
        elif prop_name == 'URL':
            url_type = params.get('TYPE', 'OTHER')
            current_card['urls'].append({
                'value': val_unescaped,
                'type': url_type
            })
        elif prop_name == 'ADR':
            # ADR: POBox;Extended;Street;Locality;Region;PostalCode;Country
            adr_parts = val_unescaped.split(';')
            while len(adr_parts) < 7:
                adr_parts.append('')
            adr_type = params.get('TYPE', 'OTHER')
            current_card['addresses'].append({
                'type': adr_type,
                'post_office_box': adr_parts[0],
                'extended_address': adr_parts[1],
                'street': adr_parts[2],
                'locality': adr_parts[3],
                'region': adr_parts[4],
                'postal_code': adr_parts[5],
                'country': adr_parts[6]
            })
        elif prop_name == 'X-SOCIALPROFILE':
            service = params.get('TYPE', 'OTHER')
            user_id = params.get('X-APPLE-USER', '')
            username = params.get('X-APPLE-USERNAME', '')
            displayname = params.get('X-APPLE-DISPLAYNAME', '')
            current_card['social_profiles'].append({
                'url': val_unescaped,
                'service': service,
                'username': username,
                'displayname': displayname,
                'user_id': user_id
            })
        elif prop_name == 'X-IM':
            service = params.get('TYPE', 'OTHER')
            current_card['instant_messages'].append({
                'username': val_unescaped,
                'service': service
            })

    return cards

def main():
    if not os.path.exists(VCF_PATH):
        print(f"Error: vCard file {VCF_PATH} not found!")
        return

    print(f"Reading vCard file: {VCF_PATH} ...")
    with open(VCF_PATH, 'r', encoding='utf-8') as f:
        vcf_content = f.read()

    print("Parsing and deconstructing vCard entries...")
    parsed_cards = parse_vcf(vcf_content)
    print(f"Successfully deconstructed {len(parsed_cards)} contacts.")

    print(f"Writing structured JSON: {JSON_OUTPUT_PATH} ...")
    with open(JSON_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(parsed_cards, f, indent=2, ensure_ascii=False)

    print("Deconstruction complete!")

if __name__ == "__main__":
    main()
