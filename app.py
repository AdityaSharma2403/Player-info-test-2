from flask import Flask, request, jsonify, send_file, Response
import requests, re, datetime, logging, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ----------------------------------
# Constants & Helper Functions (Common)
# ----------------------------------

def validate_key():
    api_key = request.args.get('key')
    if api_key != 'ADITYA':
        return False
    return True

def format_time(timestamp):
    try:
        return datetime.datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

def fetch_character_info(skill_id):
    try:
        url = f"https://character-roan.vercel.app/Character_name/Id={skill_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        name_match = re.search(r'"Character Name":\s?"(.*?)"', response.text)
        if name_match:
            return name_match.group(1)
    except:
        return None

def format_equipped_skills(equipped_skills):
    if not equipped_skills:
        return 'Not Found', []
    formatted_skills = []
    for skill in equipped_skills:
        skill_str = str(skill)
        if len(skill_str) > 1 and skill_str[-2] == '0':
            skill_str = skill_str[:-1] + '6'
        character_name = fetch_character_info(skill_str)
        if character_name:
            formatted_skills.append(character_name)
    return ', '.join(formatted_skills), []

def fetch_image(url):
    try:
        logging.info("Fetching image from %s", url)
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        logging.info("Image fetched successfully from %s", url)
        return img
    except Exception as e:
        logging.error("Error fetching image from %s: %s", url, e)
        return None

# ----------------------------------
# Composite Image Generation (Response 3)
# ----------------------------------

BG_IMAGE_URL = "https://i.ibb.co/N240RkCg/IMG-20250215-010130-294.jpg"

IMAGE_POSITIONS = {
    "HEADS": {"x": 480, "y": 60, "width": 100, "height": 100},
    "FACEPAINTS": {"x": 515, "y": 185, "width": 85, "height": 85},
    "MASKS": {"x": 495, "y": 305, "width": 100, "height": 100},
    "TOPS": {"x": 40, "y": 140, "width": 115, "height": 115},
    "SECOND_TOP": {"x": 45, "y": 315, "width": 110, "height": 110},
    "BOTTOMS": {"x": 75, "y": 485, "width": 120, "height": 115},
    "SHOES": {"x": 455, "y": 485, "width": 120, "height": 120},
    "CHARACTER": {"x": 115, "y": 100, "width": 425, "height": 525}
}

FALLBACK_ITEMS = {
    "HEADS": "211000000",
    "MASKS": "208000000",
    "FACEPAINTS": "214000000",
    "TOPS": "203000000",
    "BOTTOMS": "204000000",
    "SHOES": "205000000"
}

GITHUB_BASE_URL = "https://raw.githubusercontent.com/AdityaSharma2403/OUTFIT-S/main/{}/{}.png"
API_URL = "https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={region}"
CHARACTER_API = "https://character-roan.vercel.app/Character_name/Id={}"
OVERLAY_LAYER_URL = "https://i.ibb.co/39993PDP/IMG-20250128-032242-357-removebg.png"

def fetch_equipped_outfits(uid, region):
    try:
        response = requests.get(API_URL.format(uid=uid, region=region))
        if response.status_code == 200:
            data = response.json()
            outfits = data.get("AccountProfileInfo", {}).get("EquippedOutfit", [])
            skills = data.get("AccountProfileInfo", {}).get("EquippedSkills", [])
            return outfits, skills
        logging.error(f"API Response Error: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
    return [], []

def extract_valid_skill_code(skills):
    for skill in skills:
        skill_str = str(skill)
        if 3 <= len(skill_str) <= 5:
            return skill_str[:-1] + "6"
    return None

def assign_outfits(equipped_outfits):
    outfit_candidates = {
        "HEADS": [],
        "MASKS": [],
        "FACEPAINTS": None,
        "TOPS": None,
        "SECOND_TOP": None,
        "BOTTOMS": None,
        "SHOES": None
    }
    top_count = 0
    for outfit_id in equipped_outfits:
        outfit_id_str = str(outfit_id)
        prefix = outfit_id_str[:3]
        if prefix == "211":
            outfit_candidates["HEADS"].append(outfit_id_str)
            outfit_candidates["MASKS"].append(outfit_id_str)
        elif prefix == "214":
            if outfit_candidates["FACEPAINTS"] is None:
                outfit_candidates["FACEPAINTS"] = outfit_id_str
        elif prefix == "203":
            top_count += 1
            if top_count == 1:
                outfit_candidates["TOPS"] = outfit_id_str
            elif top_count == 2:
                outfit_candidates["SECOND_TOP"] = outfit_id_str
        elif prefix == "204":
            if outfit_candidates["BOTTOMS"] is None:
                outfit_candidates["BOTTOMS"] = outfit_id_str
        elif prefix == "205":
            if outfit_candidates["SHOES"] is None:
                outfit_candidates["SHOES"] = outfit_id_str
    return outfit_candidates

def load_category_image(category, candidate, fallback):
    if category in ["HEADS", "MASKS"]:
        for candidate_id in candidate:
            img_url = GITHUB_BASE_URL.format(category, candidate_id)
            try:
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    return Image.open(BytesIO(img_response.content)).convert("RGBA")
            except Exception as e:
                logging.warning(f"Error loading {category} with {candidate_id}: {e}")
        img_url = GITHUB_BASE_URL.format(category, fallback)
    else:
        img_url = GITHUB_BASE_URL.format(category, candidate or fallback)
    try:
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            return Image.open(BytesIO(img_response.content)).convert("RGBA")
    except Exception as e:
        logging.error(f"Error loading fallback for {category}: {e}")
    return None

def overlay_images(bg_url, outfit_items, character_id=None):
    bg = fetch_image(bg_url)
    if bg is None:
        raise Exception("Failed to load background image.")
    
    overlay_img = fetch_image(OVERLAY_LAYER_URL)
    if overlay_img:
        final_size = overlay_img.size
        bg = bg.resize(final_size, Image.LANCZOS)
        bg.paste(overlay_img, (0, 0), overlay_img)
    else:
        logging.warning("Failed to load overlay layer image; proceeding with background as is.")

    for category, pos in IMAGE_POSITIONS.items():
        if category == "CHARACTER":
            continue
        if category in ["HEADS", "MASKS"]:
            candidate_list = outfit_items.get(category, [])
            fallback = FALLBACK_ITEMS.get(category)
            img = load_category_image(category, candidate_list, fallback)
        elif category == "TOPS":
            candidate = outfit_items.get("TOPS")
            fallback = FALLBACK_ITEMS.get("TOPS")
            img = load_category_image(category, candidate, fallback)
        elif category == "SECOND_TOP":
            candidate = outfit_items.get("SECOND_TOP")
            fallback = FALLBACK_ITEMS.get("TOPS")
            img = load_category_image("TOPS", candidate, fallback)
        else:
            candidate = outfit_items.get(category)
            fallback = FALLBACK_ITEMS.get(category)
            img = load_category_image(category, candidate, fallback)
        if img:
            img = img.resize((pos["width"], pos["height"]))
            bg.paste(img, (pos["x"], pos["y"]), img)

    if character_id:
        char_url = CHARACTER_API.format(character_id)
        try:
            char_response = requests.get(char_url)
            if char_response.status_code == 200:
                char_data = char_response.json()
                char_image_url = char_data.get("Png Image")
                if char_image_url:
                    img_response = requests.get(char_image_url)
                    if img_response.status_code == 200:
                        char_img = Image.open(BytesIO(img_response.content)).convert("RGBA")
                        char_img = char_img.resize((IMAGE_POSITIONS["CHARACTER"]["width"],
                                                    IMAGE_POSITIONS["CHARACTER"]["height"]))
                        bg.paste(char_img, (IMAGE_POSITIONS["CHARACTER"]["x"],
                                            IMAGE_POSITIONS["CHARACTER"]["y"]), char_img)
        except Exception as e:
            logging.error(f"Error loading character image: {e}")
    
    output = BytesIO()
    bg.save(output, format="PNG")
    output.seek(0)
    return output

def upload_to_imgbb_from_bytes(image_bytes):
    IMGBB_API_KEY = "6899e87002a47aca9eb33ea4b57152f8"
    url = "https://api.imgbb.com/1/upload"
    image_bytes.seek(0)
    files = {"image": ("composite.png", image_bytes, "image/png")}
    data = {"key": IMGBB_API_KEY}
    response = requests.post(url, data=data, files=files)
    if response.status_code == 200:
        return response.json().get("data", {}).get("url")
    return None

# ----------------------------------
# Custom Image Generation (Response 4)
# ----------------------------------

ACCOUNT_NAME_POSITION = {"x": 62, "y": 0, "font_size": 12.5}
ACCOUNT_LEVEL_POSITION = {"x": 180, "y": 45, "font_size": 12.5}
GUILD_NAME_POSITION = {"x": 62, "y": 40, "font_size": 12.5}
AVATAR_POSITION = {"x": 0, "y": 0, "width": 60, "height": 60}
FONT_URL = "https://raw.githubusercontent.com/Thong-ihealth/arial-unicode/main/Arial-Unicode-Bold.ttf"
SCALE = 4
FALLBACK_BANNER_ID = "900000014"
FALLBACK_AVATAR_ID = "900000013"

def get_custom_font(size):
    try:
        logging.debug("Downloading custom font from %s", FONT_URL)
        response = requests.get(FONT_URL, timeout=10)
        response.raise_for_status()
        font_bytes = BytesIO(response.content)
        return ImageFont.truetype(font_bytes, int(size))
    except Exception as e:
        logging.error("Error loading custom font: %s", e)
        return ImageFont.load_default()

def get_banner_url(banner_id):
    url = f"https://raw.githubusercontent.com/AdityaSharma2403/OUTFIT-S/main/BANNERS/{banner_id}.png"
    logging.debug("Constructed banner URL: %s", url)
    return url

def get_avatar_url(avatar_id):
    url = f"https://raw.githubusercontent.com/AdityaSharma2403/OUTFIT-S/main/AVATARS/{avatar_id}.png"
    logging.debug("Constructed avatar URL: %s", url)
    return url

def generate_custom_image(data):
    account_info = data.get("AccountInfo", {})
    guild_info = data.get("GuildInfo", {})
    captain_info = data.get("captainBasicInfo", {})

    banner_id = account_info.get("AccountBannerId") or captain_info.get("bannerId") or FALLBACK_BANNER_ID
    avatar_id = account_info.get("AccountAvatarId") or captain_info.get("headPic") or FALLBACK_AVATAR_ID

    account_name = account_info.get("AccountName", "")
    account_level = account_info.get("AccountLevel", "")
    guild_name = guild_info.get("GuildName", "")

    logging.debug("Custom Image - Banner ID: %s, Avatar ID: %s", banner_id, avatar_id)

    banner_url = get_banner_url(banner_id)
    avatar_url = get_avatar_url(avatar_id)

    bg_image = fetch_image(banner_url)
    if not bg_image:
        logging.warning("Failed to load banner image, using fallback banner (%s).", FALLBACK_BANNER_ID)
        banner_url = get_banner_url(FALLBACK_BANNER_ID)
        bg_image = fetch_image(banner_url)
        if not bg_image:
            raise Exception("Failed to load banner image")

    avatar_image = fetch_image(avatar_url)
    if not avatar_image:
        logging.warning("Failed to load avatar image, using fallback avatar (%s).", FALLBACK_AVATAR_ID)
        avatar_url = get_avatar_url(FALLBACK_AVATAR_ID)
        avatar_image = fetch_image(avatar_url)
        if not avatar_image:
            raise Exception("Failed to load avatar image")

    banner_width, banner_height = bg_image.size
    logging.debug("Original banner size: %s x %s", banner_width, banner_height)

    high_res_banner_width = banner_width * SCALE
    high_res_banner_height = banner_height * SCALE
    high_res_bg = bg_image.resize((high_res_banner_width, high_res_banner_height), Image.LANCZOS)

    a_width, a_height = avatar_image.size
    new_avatar_height = high_res_banner_height
    new_avatar_width = int((a_width / a_height) * new_avatar_height)
    high_res_avatar = avatar_image.resize((new_avatar_width, new_avatar_height), Image.LANCZOS)
    logging.debug("Resized avatar to: %s x %s", new_avatar_width, new_avatar_height)

    scaled_avatar_x = AVATAR_POSITION["x"] * SCALE
    scaled_avatar_y = AVATAR_POSITION["y"] * SCALE
    high_res_bg.paste(high_res_avatar, (scaled_avatar_x, scaled_avatar_y), high_res_avatar)

    draw = ImageDraw.Draw(high_res_bg)
    scaled_account_name_x = int(ACCOUNT_NAME_POSITION["x"] * SCALE)
    scaled_account_name_y = int(ACCOUNT_NAME_POSITION["y"] * SCALE)
    scaled_account_name_font = get_custom_font(ACCOUNT_NAME_POSITION["font_size"] * SCALE)

    scaled_account_level_x = int(ACCOUNT_LEVEL_POSITION["x"] * SCALE)
    scaled_account_level_y = int(ACCOUNT_LEVEL_POSITION["y"] * SCALE)
    scaled_account_level_font = get_custom_font(ACCOUNT_LEVEL_POSITION["font_size"] * SCALE)

    scaled_guild_name_x = int(GUILD_NAME_POSITION["x"] * SCALE)
    scaled_guild_name_y = int(GUILD_NAME_POSITION["y"] * SCALE)
    scaled_guild_name_font = get_custom_font(GUILD_NAME_POSITION["font_size"] * SCALE)

    draw.text(
        (scaled_account_name_x, scaled_account_name_y),
        f"{account_name}",
        font=scaled_account_name_font,
        fill="white"
    )
    draw.text(
        (scaled_account_level_x, scaled_account_level_y),
        f"Lvl. {account_level}",
        font=scaled_account_level_font,
        fill="white"
    )
    draw.text(
        (scaled_guild_name_x, scaled_guild_name_y),
        f"{guild_name}",
        font=scaled_guild_name_font,
        fill="white"
    )

    final_image = high_res_bg.resize((banner_width, banner_height), Image.LANCZOS)
    logging.debug("Custom image creation successful.")
    output = BytesIO()
    final_image.save(output, format="PNG")
    output.seek(0)
    return output

# ----------------------------------
# Main Endpoints
# ----------------------------------

@app.route('/ADITYA-PLAYER-INFO')
def fetch_info():
    if not validate_key():
        return jsonify({"error": "Invalid API key"}), 403

    uid = request.args.get('uid')
    region = request.args.get('region')
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400

    regions = ["ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk", "cis", "bd", "na"]
    if region and region.lower() not in regions:
        return jsonify({"error": "Invalid Region. Please enter a valid region."}), 400

    search_regions = [region] if region else regions
    player_data = None
    used_region = None

    for reg in search_regions:
        api_url = f"https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={reg}"
        try:
            response = requests.get(api_url, timeout=10)
            data = response.json()
            if "AccountInfo" in data and data["AccountInfo"].get("AccountName", "Not Found") != "Not Found":
                player_data = data
                used_region = reg
                break
        except:
            pass

    if not player_data or not player_data.get("AccountInfo") or player_data["AccountInfo"].get("AccountName", "Not Found") == "Not Found":
        return jsonify({"error": "Invalid UID or Region. Please check and try again."}), 400

    account_info = player_data.get("AccountInfo", {})
    account_profile_info = player_data.get("AccountProfileInfo", {})
    captain_basic_info = player_data.get("captainBasicInfo", {})
    equipped_skills = account_profile_info.get('EquippedSkills', [])
    formatted_skills, _ = format_equipped_skills(equipped_skills)
    guild_info = player_data.get("GuildInfo", {})
    social_info = player_data.get("socialinfo", {})
    pet_info = player_data.get("petInfo", {})
    credit_score = player_data.get("creditScoreInfo", {})

    text_response = f"""
<pre>
Response 1:
Fetching details for UID `{uid}`, nickname `{account_info.get('AccountName', 'Not Found')}` in region `{used_region}`...
</pre>

<pre>
Response 2:
Account Info:
┌ 👤 ACCOUNT BASIC INFO:
├─ AccountType: `{account_info.get('AccountType', 'Not Found')}`
├─ AccountName: `{account_info.get('AccountName', 'Not Found')}`
├─ AccountUid: `{uid}`
├─ AccountRegion: `{account_info.get('AccountRegion', 'Not Found')}`
├─ AccountLevel: `{account_info.get('AccountLevel', 'Not Found')}`
├─ AccountEXP: `{account_info.get('AccountEXP', 'Not Found')}`
├─ AccountBannerId: `{account_info.get('AccountBannerId', 'Not Found')}`
├─ AccountAvatarId: `{account_info.get('AccountAvatarId', 'Not Found')}`
├─ BrRankPoint: `{account_info.get('BrRankPoint', 'Not Found')}`
├─ hasElitePass: `{account_info.get('hasElitePass', 'False')}`
├─ Role: `{account_info.get('Role', 'Not Found')}`
├─ AccountBPBadges: `{account_info.get('AccountBPBadges', 'Not Found')}`
├─ AccountBPID: `{account_info.get('AccountBPID', 'Not Found')}`
├─ AccountSeasonId: `{account_info.get('AccountSeasonId', 'Not Found')}`
├─ AccountLikes: `{account_info.get('AccountLikes', 'Not Found')}`
├─ AccountLastLogin: `{format_time(account_info.get('AccountLastLogin', 'Not Found'))}`
├─ CsRankPoint: `{account_info.get('CsRankPoint', 'Not Found')}`
├─ EquippedWeapon: `{account_info.get('EquippedWeapon', 'Not Found')}`
├─ BrMaxRank: `{account_info.get('BrMaxRank', 'Not Found')}`
├─ CsMaxRank: `{account_info.get('CsMaxRank', 'Not Found')}`
├─ AccountCreateTime: `{format_time(account_info.get('AccountCreateTime', 'Not Found'))}`
├─ Title: `{account_info.get('Title', 'Not Found')}`
├─ ReleaseVersion: `{account_info.get('ReleaseVersion', 'Not Found')}`
├─ ShowBrRank: `{account_info.get('ShowBrRank', 'Not Found')}`
└─ ShowCsRank: `{account_info.get('ShowCsRank', 'Not Found')}`
┌ 👕 ACCOUNT OVERVIEW:
├─ EquippedOutfit: `{account_profile_info.get('EquippedOutfit', 'Not Found')}`
└─ EquippedSkills: `{formatted_skills}`
┌ 🛡️ GuildInfo:
├─ GuildID: `{guild_info.get('GuildID', 'Not Found')}`
├─ GuildName: `{guild_info.get('GuildName', 'Not Found')}`
├─ GuildOwner: `{guild_info.get('GuildOwner', 'Not Found')}`
├─ GuildLevel: `{guild_info.get('GuildLevel', 'Not Found')}`
├─ GuildCapacity: `{guild_info.get('GuildCapacity', 'Not Found')}`
└─ GuildMember: `{guild_info.get('GuildMember', 'Not Found')}`
     ├─ 👤 CaptainBasicInfo:
     ├─ accountId: `{captain_basic_info.get('accountId', 'N/A')}`
     ├─ accountType: `{captain_basic_info.get('accountType', 'N/A')}`
     ├─ nickname: `{captain_basic_info.get('nickname', 'N/A')}`
     ├─ region: `{captain_basic_info.get('region', 'N/A')}`
     ├─ level: `{captain_basic_info.get('level', 'N/A')}`
     ├─ exp: `{captain_basic_info.get('exp', 'N/A')}`
     ├─ bannerId: `{captain_basic_info.get('bannerId', 'N/A')}`
     ├─ headPic: `{captain_basic_info.get('headPic', 'N/A')}`
     ├─ lastLoginAt: `{format_time(captain_basic_info.get('lastLoginAt', 'N/A'))}`
     ├─ rank: `{captain_basic_info.get('rank', 'N/A')}`
     ├─ rankingPoints: `{captain_basic_info.get('rankingPoints', 'N/A')}`
     ├─ EquippedWeapon: `{captain_basic_info.get('EquippedWeapon', 'Not Found')}`
     ├─ maxRank: `{captain_basic_info.get('maxRank', 'N/A')}`
     ├─ csMaxRank: `{captain_basic_info.get('csMaxRank', 'N/A')}`
     ├─ createAt: `{format_time(captain_basic_info.get('createAt', 'N/A'))}`
     ├─ title: `{captain_basic_info.get('title', 'N/A')}`
     ├─ releaseVersion: `{captain_basic_info.get('releaseVersion', 'N/A')}`
     ├─ showBrRank: `{captain_basic_info.get('showBrRank', 'N/A')}`
     └─ showCsRank: `{captain_basic_info.get('showCsRank', 'N/A')}`
┌ 🐾 PetInfo:
├─ id: `{pet_info.get('id', 'Not Found')}`
├─ name: `{pet_info.get('name', 'Not Found')}`
├─ level: `{pet_info.get('level', 'Not Found')}`
├─ exp: `{pet_info.get('exp', 'Not Found')}`
├─ isSelected: `{pet_info.get('isSelected', 'Not Found')}`
└─ skinId: `{pet_info.get('skinId', 'Not Found')}`
┌ 🎮 socialinfo:
├─ AccountLanguage: `{social_info.get('AccountLanguage', 'Not Found')}`
├─ AccountSignature: `{social_info.get('AccountSignature', 'Not Found')}`
└─ AccountPreferMode: `{social_info.get('AccountPreferMode', 'Not Found')}`
┌ 🏆 CreditScoreInfo:
├─ creditScore: `{credit_score.get('creditScore', 'Not Found')}`
├─ rewardState: `{credit_score.get('rewardState', '0')}`
├─ periodicSummaryStartTime: `{format_time(credit_score.get('periodicSummaryStartTime', 'Not Found'))}`
└─ periodicSummaryEndTime: `{format_time(credit_score.get('periodicSummaryEndTime', 'Not Found'))}`
</pre>
"""

    try:
        image_bytes = overlay_images(request.args.get("bg") or BG_IMAGE_URL,
                                     assign_outfits(account_profile_info.get("EquippedOutfit", [])),
                                     extract_valid_skill_code(account_profile_info.get("EquippedSkills", [])))
        imgbb_link = upload_to_imgbb_from_bytes(image_bytes)
    except Exception as e:
        logging.error(f"Error generating composite image: {e}")
        imgbb_link = "Error generating composite image."

    try:
        custom_image_bytes = generate_custom_image(player_data)
        imgbb_link_custom = upload_to_imgbb_from_bytes(custom_image_bytes)
    except Exception as e:
        logging.error(f"Error generating custom image: {e}")
        imgbb_link_custom = "Error generating custom image."

    final_html = f"""
<html>
  <head>
    <title>Player Info</title>
  </head>
  <body>
    {text_response}
    <pre>
Response 3:
Outfit Image: {imgbb_link}
    </pre>
    <pre>
Response 4:
Avatars Image: {imgbb_link_custom}
    </pre>
  </body>
</html>
"""
    return Response(final_html, mimetype='text/html')

@app.route('/generate-image', methods=['GET'])
def generate_image_route():
    uid = request.args.get("uid")
    region = request.args.get("region")
    if not uid or not region:
        return jsonify({"error": "Missing uid or region"}), 400
    if not validate_key():
        return jsonify({"error": "Invalid API key"}), 403
    bg_url = request.args.get("bg") or BG_IMAGE_URL
    equipped_outfits, equipped_skills = fetch_equipped_outfits(uid, region)
    if not equipped_outfits:
        return jsonify({"error": "No valid API response received"}), 500
    outfit_items = assign_outfits(equipped_outfits)
    character_id = extract_valid_skill_code(equipped_skills)
    try:
        final_image = overlay_images(bg_url, outfit_items, character_id)
        return send_file(final_image, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
