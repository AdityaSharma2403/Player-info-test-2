from flask import Flask, request, jsonify, Response
import requests, datetime, logging, time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ----------------------------------
# Skill Mapping Data (Based on your input)
# ----------------------------------
SKILL_MAPPING = {
    "106": {"Character Name": "Olivia"},
    "206": {"Character Name": "Kelly"},
    "306": {"Character Name": "Ford"},
    "406": {"Character Name": "Andrew"},
    "506": {"Character Name": "Nikita"},
    "606": {"Character Name": "Misha"},
    "706": {"Character Name": "Maxim"},
    "806": {"Character Name": "Kla"},
    "906": {"Character Name": "Paloma"},
    "1006": {"Character Name": "Miguel"},
    "1106": {"Character Name": "Caroline"},
    "1206": {"Character Name": "Wukong"},
    "1306": {"Character Name": "Antonio"},
    "1406": {"Character Name": "Moco"},
    "1506": {"Character Name": "Hayato"},
    "1706": {"Character Name": "Laura"},
    "1806": {"Character Name": "Rafael"},
    "1906": {"Character Name": "A124"},
    "2006": {"Character Name": "Joseph"},
    "2106": {"Character Name": "Shani"},
    "2206": {"Character Name": "Alok"},
    "2306": {"Character Name": "Alvaro"},
    "2406": {"Character Name": "Notora"},
    "2506": {"Character Name": "Kelly The Swift"},
    "2606": {"Character Name": "Steffie"},
    "2706": {"Character Name": "Jota"},
    "2806": {"Character Name": "Kapella"},
    "2906": {"Character Name": "Luqueta"},
    "3006": {"Character Name": "Wolfrahh"},
    "3106": {"Character Name": "Clu"},
    "3206": {"Character Name": "Elite Hayato"},
    "3306": {"Character Name": "Jai"},
    "3406": {"Character Name": "K"},
    "3506": {"Character Name": "Dasha"},
    "3806": {"Character Name": "Chrono"},
    "4006": {"Character Name": "Skyler"},
    "4106": {"Character Name": "Shirou"},
    "4206": {"Character Name": "Andrew the Fierce"},
    "4306": {"Character Name": "Maro"},
    "4406": {"Character Name": "Xayne"},
    "4506": {"Character Name": "D-Bee"},
    "4606": {"Character Name": "Thiva"},
    "4706": {"Character Name": "Dimitri"},
    "4806": {"Character Name": "Moco Enigma"},
    "4906": {"Character Name": "Leon"},
    "5006": {"Character Name": "Otho"},
    "5206": {"Character Name": "Nairi"},
    "5306": {"Character Name": "Luna"},
    "5406": {"Character Name": "Kenta"},
    "5506": {"Character Name": "Homer"},
    "5606": {"Character Name": "Iris"},
    "5706": {"Character Name": "J.Biebs"},
    "5806": {"Character Name": "Tatsuya"},
    "6006": {"Character Name": "Santino"},
    "6206": {"Character Name": "Orion"},
    "6306": {"Character Name": "Alvaro Rageblast"},
    "6506": {"Character Name": "Sonia"},
    "6606": {"Character Name": "Suzy"},
    "6706": {"Character Name": "Ignis"},
    "22016": {"Character Name": "Awakened Alok"},
    "6906": {"Character Name": "Kairos"},
    "7106": {"Character Name": "Lila"},
    "7006": {"Character Name": "Kassie"},
    "6806": {"Character Name": "Ryden"},
    "7206": {"Character Name": "Koda"}
}

# ----------------------------------
# Helper Functions
# ----------------------------------
def validate_key():
    api_key = request.args.get('key')
    return api_key == 'ADITYA'

def format_custom_time(dt_str):
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    formatted_time = dt.strftime("%d %B %Y %I:%M:%S %p")
    return formatted_time[:-2] + formatted_time[-2:].lower()

def format_time(ts):
    try:
        if ts == "Not Found":
            return ts
        ts_int = int(ts)
        dt = datetime.datetime.utcfromtimestamp(ts_int)
        return format_custom_time(dt.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logging.error("Error formatting time: %s", e)
        return ts

def get_skill_info(skill_id):
    return SKILL_MAPPING.get(str(skill_id), {"Character Name": f"Unknown ({skill_id})", "Skill id": str(skill_id), "Png Image": "Not Found"})

def format_equipped_skills(equipped_skills):
    """
    Loops through all equipped skill IDs (ignoring any IDs in the skip list),
    transforms each ID if needed, retrieves its corresponding name, and returns
    a comma-separated list where the first valid skill is marked with (P) and the rest with (A).
    """
    if not equipped_skills:
        return 'Not Found'
        
    skip_ids = {"8", "16", "3", "2", "1"}
    names = []
    for skill in equipped_skills:
        skill_str = str(skill)
        if skill_str in skip_ids:
            continue
        if len(skill_str) > 0 and skill_str[-1] != "6":
            transformed_skill = skill_str[:-1] + "6"
        else:
            transformed_skill = skill_str
        info = get_skill_info(transformed_skill)
        marker = "(P)" if len(names) == 0 else "(A)"
        names.append(f"{info['Character Name']} {marker}")
    return ', '.join(names) if names else 'Not Found'

def get_rank_text(score):
    try:
        score = int(score)
    except:
        return "Bronze"
    if 1000 <= score <= 1199:
        return "Bronze I"
    elif 1200 <= score <= 1399:
        return "Bronze II"
    elif 1400 <= score <= 1599:
        return "Bronze III"
    elif 1600 <= score <= 1799:
        return "Bronze IV"
    elif 1800 <= score <= 1999:
        return "Silver I"
    elif 2000 <= score <= 2199:
        return "Silver II"
    elif 2200 <= score <= 2399:
        return "Silver III"
    elif 2400 <= score <= 2599:
        return "Silver IV"
    elif 2600 <= score <= 2799:
        return "Gold I"
    elif 2800 <= score <= 2999:
        return "Gold II"
    elif 3000 <= score <= 3199:
        return "Gold III"
    elif 3200 <= score <= 3399:
        return "Gold IV"
    elif 3400 <= score <= 3599:
        return "Platinum I"
    elif 3600 <= score <= 3799:
        return "Platinum II"
    elif 3800 <= score <= 3999:
        return "Platinum III"
    elif 4000 <= score <= 4199:
        return "Platinum IV"
    elif 4200 <= score <= 4399:
        return "Diamond I"
    elif 4400 <= score <= 4599:
        return "Diamond II"
    elif 4600 <= score <= 4799:
        return "Diamond III"
    elif 4800 <= score <= 4999:
        return "Diamond IV"
    elif 5000 <= score <= 5999:
        return "Heroic"
    elif 6000 <= score <= 6999:
        return "Elite Heroic"
    elif 7000 <= score <= 7999:
        return "Master"
    elif 8000 <= score <= 8999:
        return "Elite Master"
    elif score >= 9000:
        return "Grandmaster"
    else:
        return "Unknown"

def format_equipped_id(original_id, prefix):
    """
    Transforms the equipped weapon id so that its first three digits are replaced by the given prefix.
    For example, if original_id is '123456789' and prefix is '907', the result will be '907456789'.
    If no equipped id is provided, returns "Not Equipped".
    """
    if original_id in ['Not Found', None, '']:
        return "Not Equipped"
    s = str(original_id)
    if len(s) >= 3:
        return prefix + s[3:]
    else:
        return prefix

def get_title_name(title):
    """
    Given a title number, fetches the cosmetic item info and returns the Name from the response.
    """
    if title in [None, 'Not Found', '']:
        return 'Not Found'
    try:
        url = f"https://free-fire-item-info-api.vercel.app/akiru-items-info?option=1&items={title}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('Name', title)
        return title
    except Exception as e:
        logging.error("Error fetching title info: %s", e)
        return title

def extract_first_code(value):
    """
    If the equipped weapon value contains multiple codes (as a list or comma-separated string),
    extract and return only the first code.
    """
    if isinstance(value, list):
        return str(value[0]) if value else "Not Found"
    elif isinstance(value, str):
        if "," in value:
            return value.split(",")[0].strip()
        return value.strip()
    return "Not Found"

# ----------------------------------
# Data Fetching from External API
# ----------------------------------
API_URL = "https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={region}"

def fetch_player_data(uid, region):
    try:
        response = requests.get(API_URL.format(uid=uid, region=region))
        if response.status_code == 200:
            return response.json()
        logging.error("API Response Error: %s", response.status_code)
    except Exception as e:
        logging.error("Error fetching data: %s", e)
    return None

# ----------------------------------
# Main Endpoint
# ----------------------------------
@app.route('/ADITYA-PLAYER-INFO')
def fetch_info():
    start_time = time.time()

    if not validate_key():
        return jsonify({"error": "Invalid API key"}), 403

    uid = request.args.get('uid')
    region = request.args.get('region')
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400

    valid_regions = ["ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk", "cis", "bd", "na"]
    if region and region.lower() not in valid_regions:
        return jsonify({"error": "Invalid Region. Please enter a valid region."}), 400

    search_regions = [region] if region else valid_regions
    player_data = None
    used_region = None

    for reg in search_regions:
        data = fetch_player_data(uid, reg)
        if data and "AccountInfo" in data and data["AccountInfo"].get("AccountName", "Not Found") != "Not Found":
            player_data = data
            used_region = reg
            break

    if not player_data or not player_data.get("AccountInfo") or player_data["AccountInfo"].get("AccountName", "Not Found") == "Not Found":
        return jsonify({"error": "Invalid UID or Region. Please check and try again."}), 400

    account_info = player_data.get("AccountInfo", {})
    account_profile_info = player_data.get("AccountProfileInfo", {})
    captain_basic_info = player_data.get("captainBasicInfo", {})
    guild_info = player_data.get("GuildInfo", {})
    social_info = player_data.get("socialinfo", {})
    pet_info = player_data.get("petInfo", {})
    credit_score = player_data.get("creditScoreInfo", {})

    formatted_skills = format_equipped_skills(account_profile_info.get('EquippedSkills', []))
    create_time = format_time(account_info.get('AccountCreateTime', 'Not Found'))
    last_login = format_time(account_info.get('AccountLastLogin', 'Not Found'))

    # Get rank texts
    br_rank = get_rank_text(account_info.get('BrRankPoint', 'Not Found'))
    captain_br_rank = get_rank_text(captain_basic_info.get('rankingPoints', 'N/A'))

    # If EquippedWeapon contains multiple codes, extract only the first one.
    weapon_value = account_info.get('EquippedWeapon', 'Not Found')
    first_weapon_value = extract_first_code(weapon_value)

    # Format equipped IDs with respective prefixes
    gun_id = format_equipped_id(first_weapon_value, "907")
    animation_id = format_equipped_id(first_weapon_value, "912")
    transform_animation_id = format_equipped_id(first_weapon_value, "914")

    # Get title names from API
    title_name = get_title_name(account_info.get('Title', 'Not Found'))
    leader_title_name = get_title_name(captain_basic_info.get('title', 'Not Found'))
    # Fetch pet type name similarly
    pet_type_name = get_title_name(pet_info.get('id', 'Not Found'))

    response_message = f"""
ACCOUNT INFO:
┌ 👤 ACCOUNT BASIC INFO
├─ Name: {account_info.get('AccountName', 'Not Found')}
├─ UID: {uid}
├─ Level: {account_info.get('AccountLevel', 'Not Found')} (Exp: {account_info.get('AccountEXP', 'Not Found')})
├─ Region: {account_info.get('AccountRegion', 'Not Found')}
├─ Likes: {account_info.get('AccountLikes', 'Not Found')}
├─ Honor Score: {credit_score.get('creditScore', 'Not Found')}
├─ Title: {title_name}
└─ Signature: {social_info.get('AccountSignature', 'Not Found')}

┌ 🎮 ACCOUNT ACTIVITY
├─ Most Recent OB: {account_info.get('ReleaseVersion', 'Not Found')}
├─ Fire Pass: {account_info.get('hasElitePass', 'False')}
├─ Current BP Badges: {account_info.get('AccountBPBadges', 'Not Found')}
├─ BR Rank: {br_rank} ({account_info.get('BrRankPoint', 'Not Found')})
├─ CS Points: {account_info.get('CsRankPoint', 'Not Found')}
├─ Created At: {create_time}
└─ Last Login: {last_login}

┌ 👕 ACCOUNT OVERVIEW
├─ Avatar ID: {account_info.get('AccountAvatarId', 'Default')}
├─ Banner ID: {account_info.get('AccountBannerId', 'Default')}
├─ Pin ID: 910044001
├─ Equipped Skill: {formatted_skills}
├─ Equipped Gun ID: {gun_id}
├─ Equipped Animation ID: {animation_id}
├─ Transform Animation ID: {transform_animation_id}
└─ Outfits: Graphically Presented Below! 😉

┌ 🐾 PetInfo:
├─ Equipped?: {pet_info.get('isSelected', 'Not Found')}
├─ Pet Name: {pet_info.get('name', pet_type_name)}
├─ Pet Type: {pet_type_name}
├─ Pet Exp: {pet_info.get('exp', 'Not Found')}
└─ Pet Level: {pet_info.get('level', 'Not Found')}

┌ 🛡️ GUILD INFO
├─ Guild Name: {guild_info.get('GuildName', 'Not Found')}
├─ Guild ID: {guild_info.get('GuildID', 'Not Found')}
├─ Guild Level: {guild_info.get('GuildLevel', 'Not Found')}
├─ Live Members: {guild_info.get('GuildMember', 'Not Found')}
└─ Leader Info:
    ├─ Leader Name: {captain_basic_info.get('nickname', 'N/A')}
    ├─ Leader UID: {captain_basic_info.get('accountId', 'N/A')}
    ├─ Leader Level: {captain_basic_info.get('level', 'N/A')} (Exp: {captain_basic_info.get('exp', 'N/A')})
    ├─ Leader Created At: {format_time(captain_basic_info.get('createAt', 'N/A'))}
    ├─ Leader Last Login: {format_time(captain_basic_info.get('lastLoginAt', 'N/A'))}
    ├─ Leader Title: {leader_title_name}
    ├─ Leader BR Points: {captain_br_rank} {captain_basic_info.get('rankingPoints', 'N/A')}
    └─ Leader CS Points: {captain_basic_info.get('rank', 'N/A')}
"""
    # Ensure the response is sent after at least 1 second
    elapsed = time.time() - start_time
    if elapsed < 1:
        time.sleep(1 - elapsed)

    return Response(response_message, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
