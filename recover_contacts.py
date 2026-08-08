#!/usr/bin/env python3
import os
import re
import csv
import plistlib
import datetime

# Directory settings
INPUT_DIR = "/Users/ricardo/Desktop/all i need"
OUTPUT_CSV = "/Users/ricardo/Desktop/recovered_contacts.csv"
OUTPUT_VCF = "/Users/ricardo/Desktop/recovered_contacts.vcf"

def clean_label(label):
    if not label:
        return ""
    # Remove standard Apple wrappers: _$!<Home>!$_ or X-_$!<Work>!$_
    m = re.search(r'_\$!<([^>]+)>!\$_', label)
    if m:
        val = m.group(1)
        # Check for prefix
        prefix = label.split('_$!<')[0]
        if prefix:
            # Strip trailing dash
            if prefix.endswith('-'):
                prefix = prefix[:-1]
            return f"{prefix} {val}".strip()
        return val
    return label

def map_vcf_type(label):
    label_lower = label.lower()
    if 'mobile' in label_lower or 'cell' in label_lower:
        return 'CELL'
    elif 'home' in label_lower:
        return 'HOME'
    elif 'work' in label_lower:
        return 'WORK'
    elif 'fax' in label_lower:
        return 'FAX'
    elif 'pager' in label_lower:
        return 'PAGER'
    elif 'main' in label_lower:
        return 'MAIN'
    # Default to uppercase of cleaned label if alphanumeric
    clean = re.sub(r'[^a-zA-Z0-9]', '', label)
    return clean.upper() if clean else 'OTHER'

def escape_vcf(val):
    if not val:
        return ""
    val = str(val)
    # Escape backslashes, semicolons, commas, and newlines
    val = val.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    val = val.replace('\n', '\\n').replace('\r', '')
    return val

def format_address_csv(addr_dict):
    parts = []
    # Try keys commonly found in ABAddress
    for k in ['Street', 'City', 'State', 'ZIP', 'Country']:
        if k in addr_dict and addr_dict[k]:
            parts.append(str(addr_dict[k]))
    return ", ".join(parts)

def parse_contact_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = plistlib.load(f)
    except Exception as e:
        print(f"Error reading {os.path.basename(filepath)}: {e}")
        return None

    contact = {
        'uid': data.get('UID', ''),
        'first_name': data.get('First', ''),
        'middle_name': data.get('Middle', ''),
        'last_name': data.get('Last', ''),
        'nickname': data.get('Nickname', ''),
        'title': data.get('Title', ''),
        'organization': data.get('Organization', ''),
        'job_title': data.get('JobTitle', ''),
        'note': data.get('Note', ''),
        'birthday': None,
        'phones': [],
        'emails': [],
        'addresses': [],
        'urls': [],
        'social_profiles': [],
        'instant_messages': [],
        'creation_date': data.get('Creation'),
        'modification_date': data.get('Modification'),
    }

    # Format birthday
    bday = data.get('Birthday')
    if isinstance(bday, datetime.datetime):
        contact['birthday'] = bday.strftime('%Y-%m-%d')
    elif bday:
        contact['birthday'] = str(bday)

    # Helper to parse multi-value plists
    # Format of property is: {'identifiers': [...], 'labels': [...], 'primary': ..., 'values': [...]}
    def extract_multi(prop_key, value_formatter):
        prop_data = data.get(prop_key)
        if not prop_data or not isinstance(prop_data, dict):
            return []
        
        identifiers = prop_data.get('identifiers', [])
        labels = prop_data.get('labels', [])
        values = prop_data.get('values', [])
        
        extracted = []
        for i in range(min(len(labels), len(values))):
            lbl = clean_label(labels[i])
            val = values[i]
            formatted_val = value_formatter(val)
            extracted.append({
                'label': lbl,
                'raw_label': labels[i],
                'value': val,
                'formatted': formatted_val
            })
        return extracted

    # Extract multi-values
    contact['phones'] = extract_multi('Phone', lambda x: str(x).strip())
    contact['emails'] = extract_multi('Email', lambda x: str(x).strip())
    contact['urls'] = extract_multi('URLs', lambda x: str(x).strip())
    
    # Extract Address
    def format_addr(val):
        if isinstance(val, dict):
            return val
        return {'Street': str(val)}
    contact['addresses'] = extract_multi('Address', format_addr)
    
    # Extract Social Profiles
    def format_social(val):
        if isinstance(val, dict):
            return val
        return {'url': str(val)}
    contact['social_profiles'] = extract_multi('SocialProfile', format_social)
    
    # Extract Instant Messages
    def format_im(val):
        if isinstance(val, dict):
            return val
        return {'InstantMessageUsername': str(val)}
    contact['instant_messages'] = extract_multi('InstantMessage', format_im)

    # Fallback to YahooInstant if present and no instant messages are extracted
    if not contact['instant_messages'] and 'YahooInstant' in data:
        contact['instant_messages'] = extract_multi('YahooInstant', lambda x: {'InstantMessageService': 'YahooInstant', 'InstantMessageUsername': str(x)})

    return contact

def generate_vcard(c):
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    
    # Structured name (N)
    last = escape_vcf(c['last_name'])
    first = escape_vcf(c['first_name'])
    middle = escape_vcf(c['middle_name'])
    title_pref = escape_vcf(c['title'])
    lines.append(f"N:{last};{first};{middle};{title_pref};")
    
    # Formatted name (FN)
    fn_parts = [p for p in [c['title'], c['first_name'], c['middle_name'], c['last_name']] if p]
    fn = " ".join(fn_parts)
    if not fn:
        # Fallback to organization
        fn = c['organization']
    lines.append(f"FN:{escape_vcf(fn)}")
    
    if c['nickname']:
        lines.append(f"NICKNAME:{escape_vcf(c['nickname'])}")
    
    if c['organization']:
        lines.append(f"ORG:{escape_vcf(c['organization'])}")
        
    if c['job_title']:
        lines.append(f"TITLE:{escape_vcf(c['job_title'])}")
        
    if c['note']:
        lines.append(f"NOTE:{escape_vcf(c['note'])}")
        
    if c['birthday']:
        lines.append(f"BDAY:{c['birthday']}")
        
    for phone in c['phones']:
        vcf_type = map_vcf_type(phone['label'])
        lines.append(f"TEL;TYPE={vcf_type}:{escape_vcf(phone['value'])}")
        
    for email in c['emails']:
        vcf_type = map_vcf_type(email['label'])
        lines.append(f"EMAIL;TYPE={vcf_type}:{escape_vcf(email['value'])}")
        
    for addr in c['addresses']:
        val = addr['formatted']
        street = escape_vcf(val.get('Street', ''))
        city = escape_vcf(val.get('City', ''))
        state = escape_vcf(val.get('State', ''))
        zipcode = escape_vcf(val.get('ZIP', ''))
        country = escape_vcf(val.get('Country', ''))
        vcf_type = map_vcf_type(addr['label'])
        lines.append(f"ADR;TYPE={vcf_type}:;;{street};{city};{state};{zipcode};{country}")
        
    for url in c['urls']:
        vcf_type = map_vcf_type(url['label'])
        lines.append(f"URL;TYPE={vcf_type}:{escape_vcf(url['value'])}")
        
    for soc in c['social_profiles']:
        val = soc['formatted']
        service = escape_vcf(val.get('serviceName', soc['label'] or 'OTHER'))
        user_id = escape_vcf(val.get('userIdentifier', ''))
        username = escape_vcf(val.get('username', ''))
        display = escape_vcf(val.get('displayname', ''))
        url_val = escape_vcf(val.get('url', ''))
        
        attrs = []
        if user_id:
            attrs.append(f"x-apple-user={user_id}")
        if username:
            attrs.append(f"x-apple-username={username}")
        if display:
            attrs.append(f"x-apple-displayname={display}")
            
        attr_str = ";" + ";".join(attrs) if attrs else ""
        lines.append(f"X-SOCIALPROFILE;TYPE={service.lower()}{attr_str}:{url_val}")
        
    for im in c['instant_messages']:
        val = im['formatted']
        service = escape_vcf(val.get('InstantMessageService', im['label'] or 'OTHER'))
        username = escape_vcf(val.get('InstantMessageUsername', ''))
        lines.append(f"X-IM;TYPE={service.lower()}:{username}")
        
    if isinstance(c['modification_date'], datetime.datetime):
        lines.append(f"REV:{c['modification_date'].strftime('%Y-%m-%dT%H:%M:%SZ')}")
        
    if c['uid']:
        lines.append(f"UID:{escape_vcf(c['uid'])}")
        
    lines.append("END:VCARD")
    return "\n".join(lines) + "\n"

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Input directory {INPUT_DIR} does not exist!")
        return

    print("Scanning input directory for contacts...")
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.abcdp')]
    print(f"Found {len(files)} potential contact files.")

    contacts = []
    for f in files:
        filepath = os.path.join(INPUT_DIR, f)
        c = parse_contact_file(filepath)
        if c:
            contacts.append(c)

    print(f"Parsed {len(contacts)} contacts successfully. Writing CSV...")

    # Write CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'UID', 'First Name', 'Middle Name', 'Last Name', 'Nickname', 
            'Title', 'Organization', 'Job Title', 'Birthday', 
            'Phones', 'Emails', 'Addresses', 'URLs', 'Social Profiles', 
            'Instant Messages', 'Note', 'Created Date', 'Modified Date'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for c in contacts:
            # Flatten multi-values for CSV
            phones_str = "; ".join([f"{p['label']}: {p['value']}" if p['label'] else p['value'] for p in c['phones']])
            emails_str = "; ".join([f"{e['label']}: {e['value']}" if e['label'] else e['value'] for e in c['emails']])
            urls_str = "; ".join([f"{u['label']}: {u['value']}" if u['label'] else u['value'] for u in c['urls']])
            
            addrs_str = "; ".join([
                f"{a['label']}: {format_address_csv(a['formatted'])}" if a['label'] else format_address_csv(a['formatted'])
                for a in c['addresses']
            ])
            
            socials_str = "; ".join([
                f"{s['label'] or s['formatted'].get('serviceName', 'OTHER')}: {s['formatted'].get('username', '')} ({s['formatted'].get('displayname', '')})"
                for s in c['social_profiles']
            ])
            
            ims_str = "; ".join([
                f"{i['formatted'].get('InstantMessageService', i['label'] or 'OTHER')}: {i['formatted'].get('InstantMessageUsername', '')}"
                for i in c['instant_messages']
            ])

            writer.writerow({
                'UID': c['uid'],
                'First Name': c['first_name'],
                'Middle Name': c['middle_name'],
                'Last Name': c['last_name'],
                'Nickname': c['nickname'],
                'Title': c['title'],
                'Organization': c['organization'],
                'Job Title': c['job_title'],
                'Birthday': c['birthday'],
                'Phones': phones_str,
                'Emails': emails_str,
                'Addresses': addrs_str,
                'URLs': urls_str,
                'Social Profiles': socials_str,
                'Instant Messages': ims_str,
                'Note': c['note'],
                'Created Date': c['creation_date'].isoformat() if c['creation_date'] else '',
                'Modified Date': c['modification_date'].isoformat() if c['modification_date'] else ''
            })

    print(f"CSV exported to: {OUTPUT_CSV}")
    print("Writing merged VCF...")

    # Write VCF
    with open(OUTPUT_VCF, 'w', encoding='utf-8') as vcffile:
        for c in contacts:
            vcffile.write(generate_vcard(c))

    print(f"VCF exported to: {OUTPUT_VCF}")
    print("Recovery complete!")

if __name__ == "__main__":
    main()
