"""
Crop profiles used by the soil, weather, calendar, and risk modules.

Covers both major Indian smallholder crops and all 14 crops present in the
38-class PlantVillage dataset so every leaf class maps to an agronomic profile.

Sources (for the project report):
  * Preferred soil pH: FAO crop ecological requirements (ECOCROP) and Indian
    state agricultural university package-of-practices.
  * Salt sensitivity class: Maas & Hoffman (1977); FAO Irrigation and
    Drainage Paper 29 (Ayers & Westcot, 1985).
  * Heat / cold stress temperatures: general crop-physiology literature
    (e.g. Hatfield & Prueger 2015, Weather and Climate Extremes 10:4-10).
"""

CROP_PROFILES = {
    "tomato": {
        "name": "Tomato", "ph": (6.0, 7.0), "salt": "moderately sensitive",
        "heat_tmax": 35, "cold_tmin": 10, "duration_days": 115,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["early_blight", "late_blight", "bacterial_spot", "septoria_leaf_spot", "leaf_mold", "yellow_leaf_curl_virus", "mosaic_virus", "spider_mites", "target_spot"],
        "heat_note": "Day temperatures above about 35°C cause flower drop and poor fruit set in tomato.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Nursery & Transplanting (Days 0–25)", "tasks": "Use healthy disease-free seedlings, maintain nursery drainage, and install yellow sticky traps before transplanting."},
            {"stage": "vegetative", "days": (26, 45), "title": "Vegetative Growth (Days 26–45)", "tasks": "Weed regularly, earth up soil around stems, stake indeterminate varieties, and scout lower leaves for early blight."},
            {"stage": "flowering", "days": (46, 70), "title": "Flowering & Fruit Set (Days 46–70)", "tasks": "Maintain steady soil moisture to prevent flower drop and blossom-end rot. Watch for whiteflies and leaf curl."},
            {"stage": "fruiting", "days": (71, 95), "title": "Fruit Development (Days 71–95)", "tasks": "Remove diseased lower leaves to improve airflow, avoid overhead watering, and monitor for fruit borers and late blight."},
            {"stage": "maturity", "days": (96, 125), "title": "Harvesting & Residue Cleanup (Days 96+)", "tasks": "Harvest at breaker/ripe stage as per market distance. Remove and destroy infected crop residues after final picking."},
        ],
    },
    "potato": {
        "name": "Potato", "ph": (5.0, 6.5), "salt": "moderately sensitive",
        "heat_tmax": 30, "cold_tmin": 2, "duration_days": 100,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["late_blight", "early_blight"],
        "heat_note": "Potato tuber formation slows down when temperatures stay above about 30°C.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Sprouting & Emergence (Days 0–20)", "tasks": "Plant certified disease-free seed tubers at proper ridge spacing and avoid waterlogging."},
            {"stage": "vegetative", "days": (21, 40), "title": "Stolon Formation & Earthing Up (Days 21–40)", "tasks": "Perform earthing-up to cover developing tubers and prevent greening."},
            {"stage": "flowering", "days": (41, 65), "title": "Tuber Initiation & Bulking (Days 41–65)", "tasks": "Critical water requirement stage. Scout daily during cool, humid weather for Late Blight water-soaked lesions."},
            {"stage": "fruiting", "days": (66, 85), "title": "Late Tuber Bulking (Days 66–85)", "tasks": "Keep ridges intact so spores do not wash down to tubers. Avoid excess irrigation."},
            {"stage": "maturity", "days": (86, 110), "title": "Skin Set & Harvest (Days 86+)", "tasks": "Stop irrigation 10–12 days before harvest for firm skin set. Sort out any blighted tubers before storage."},
        ],
    },
    "pepper": {
        "name": "Bell Pepper / Capsicum", "ph": (6.0, 7.0), "salt": "moderately sensitive",
        "heat_tmax": 35, "cold_tmin": 12, "duration_days": 120,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["bacterial_spot", "powdery_mildew"],
        "heat_note": "Very hot weather (above about 35°C) causes flower and fruit drop in capsicum.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Seedling & Establishment (Days 0–25)", "tasks": "Transplant healthy seedlings on raised beds with good drainage."},
            {"stage": "vegetative", "days": (26, 45), "title": "Branching & Canopy Growth (Days 26–45)", "tasks": "Keep beds weed-free, mulch if possible, and check underside of leaves for thrips and mites."},
            {"stage": "flowering", "days": (46, 70), "title": "Flowering & Fruit Set (Days 46–70)", "tasks": "Avoid moisture stress during flowering. Do not handle wet plants if bacterial spot is present."},
            {"stage": "fruiting", "days": (71, 100), "title": "Fruit Development (Days 71–100)", "tasks": "Support heavy branches and remove damaged fruits promptly."},
            {"stage": "maturity", "days": (101, 130), "title": "Harvesting (Days 101+)", "tasks": "Harvest mature fruits with clean secateurs and rotate with non-solanaceous crops next season."},
        ],
    },
    "chilli": {
        "name": "Chilli", "ph": (6.0, 7.0), "salt": "moderately sensitive",
        "heat_tmax": 35, "cold_tmin": 12, "duration_days": 135,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["bacterial_spot", "powdery_mildew"],
        "heat_note": "Very hot weather (above about 35°C) causes flower and fruit drop in chilli.",
        "stages": [
            {"stage": "seedling", "days": (0, 30), "title": "Nursery & Transplanting (Days 0–30)", "tasks": "Raise seedlings under insect-proof net to prevent early virus transmission."},
            {"stage": "vegetative", "days": (31, 55), "title": "Vegetative Growth (Days 31–55)", "tasks": "Monitor for leaf curl (thrips/mites/whiteflies) and rogue out virus-infected plants early."},
            {"stage": "flowering", "days": (56, 85), "title": "Flowering & Pod Set (Days 56–85)", "tasks": "Irrigate lightly and regularly; avoid water stagnation in the root zone."},
            {"stage": "fruiting", "days": (86, 115), "title": "Pod Development (Days 86–115)", "tasks": "Scout for powdery mildew and fruit rot during humid spells."},
            {"stage": "maturity", "days": (116, 150), "title": "Picking & Drying (Days 116+)", "tasks": "Pick ripe pods in dry weather and dry on clean tarpaulins to prevent aflatoxin."},
        ],
    },
    "maize": {
        "name": "Maize (Corn)", "ph": (5.8, 7.0), "salt": "moderately sensitive",
        "heat_tmax": 35, "cold_tmin": 10, "duration_days": 105,
        "fym_tonnes_per_acre": (5, 6),
        "common_diseases": ["common_rust", "northern_leaf_blight", "gray_leaf_spot"],
        "heat_note": "Heat above about 35°C at tasseling and silking reduces pollination in maize.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Emergence & Seedling (Days 0–20)", "tasks": "Ensure uniform stand, prevent waterlogging, and scout whorls for Fall Armyworm."},
            {"stage": "vegetative", "days": (21, 50), "title": "Knee-High to Grand Growth (Days 21–50)", "tasks": "Inter-cultivate, earth up ridges, and inspect lower leaves for blight or rust lesions."},
            {"stage": "flowering", "days": (51, 70), "title": "Tasseling & Silking (Days 51–70)", "tasks": "Most critical stage for soil moisture — moisture stress here severely cuts cob grain setting."},
            {"stage": "fruiting", "days": (71, 95), "title": "Cob & Grain Filling (Days 71–95)", "tasks": "Maintain healthy upper canopy leaves for grain filling."},
            {"stage": "maturity", "days": (96, 115), "title": "Black-Layer Maturity & Harvest (Days 96+)", "tasks": "Harvest when husks turn dry and papery; dry cobs well before shelling."},
        ],
    },
    "rice": {
        "name": "Rice (Paddy)", "ph": (5.5, 7.0), "salt": "sensitive",
        "heat_tmax": 35, "cold_tmin": 15, "duration_days": 125,
        "fym_tonnes_per_acre": (5, 6),
        "common_diseases": [],
        "heat_note": "Temperatures above about 35°C during flowering can cause empty grains in rice.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Nursery & Transplanting (Days 0–25)", "tasks": "Transplant 21–25 day old seedlings at shallow depth; watch for zinc deficiency ('khaira') in alkaline soils."},
            {"stage": "vegetative", "days": (26, 55), "title": "Active Tillering (Days 26–55)", "tasks": "Maintain shallow water (2–5 cm) with alternate wetting and drying to strengthen roots."},
            {"stage": "flowering", "days": (56, 85), "title": "Panicle Initiation & Booting (Days 56–85)", "tasks": "Ensure adequate water and scout lower stems for sheath blight and planthoppers."},
            {"stage": "fruiting", "days": (86, 105), "title": "Flowering & Milk/Dough Grain (Days 86–105)", "tasks": "Avoid water deficit during flowering."},
            {"stage": "maturity", "days": (106, 130), "title": "Ripening & Harvest (Days 106+)", "tasks": "Drain field 10 days before harvest when 80% of panicles turn golden yellow."},
        ],
    },
    "cotton": {
        "name": "Cotton", "ph": (5.8, 8.0), "salt": "tolerant",
        "heat_tmax": 38, "cold_tmin": 15, "duration_days": 150,
        "fym_tonnes_per_acre": (5, 6),
        "common_diseases": [],
        "heat_note": "Very high temperatures (above about 38°C) increase square and boll shedding in cotton.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Emergence & Seedling (Days 0–25)", "tasks": "Gap-fill early and keep rows weed-free."},
            {"stage": "vegetative", "days": (26, 55), "title": "Vegetative & Square Initiation (Days 26–55)", "tasks": "Scout for sucking pests (jassids, aphids, whiteflies) using yellow sticky traps."},
            {"stage": "flowering", "days": (56, 95), "title": "Flowering & Boll Formation (Days 56–95)", "tasks": "Monitor pheromone traps for pink bollworm and destroy rosette flowers."},
            {"stage": "fruiting", "days": (96, 125), "title": "Boll Development (Days 96–125)", "tasks": "Prevent waterlogging during heavy rains and watch for foliar reddening (Mg/N stress)."},
            {"stage": "maturity", "days": (126, 160), "title": "Boll Opening & Picking (Days 126+)", "tasks": "Pick clean, dry seed cotton in morning hours after dew dries; shred stalks promptly after final picking."},
        ],
    },
    "wheat": {
        "name": "Wheat", "ph": (6.0, 7.5), "salt": "moderately tolerant",
        "heat_tmax": 32, "cold_tmin": 2, "duration_days": 120,
        "fym_tonnes_per_acre": (4, 6),
        "common_diseases": [],
        "heat_note": "Terminal heat (above about 32°C) during grain filling reduces wheat grain weight.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Emergence (Days 0–20)", "tasks": "Ensure timely sowing and adequate seedbed moisture."},
            {"stage": "vegetative", "days": (21, 50), "title": "Crown Root Initiation & Tillering (Days 21–50)", "tasks": "First irrigation at CRI stage (21 days after sowing) is critical for tiller formation."},
            {"stage": "flowering", "days": (51, 85), "title": "Jointing, Booting & Heading (Days 51–85)", "tasks": "Scout leaves for yellow or brown rust pustules during cool, humid weather."},
            {"stage": "fruiting", "days": (86, 105), "title": "Milk & Dough Stage (Days 86–105)", "tasks": "Light irrigation in calm weather helps mitigate terminal heat stress."},
            {"stage": "maturity", "days": (106, 125), "title": "Ripening & Harvest (Days 106+)", "tasks": "Harvest when grain moisture drops below 14%."},
        ],
    },
    "groundnut": {
        "name": "Groundnut", "ph": (6.0, 7.0), "salt": "moderately sensitive",
        "heat_tmax": 35, "cold_tmin": 15, "duration_days": 110,
        "fym_tonnes_per_acre": (4, 5),
        "common_diseases": [],
        "heat_note": "Temperatures above about 35°C reduce flowering and peg formation in groundnut.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Emergence (Days 0–20)", "tasks": "Ensure friable, well-drained soil for healthy root nodulation."},
            {"stage": "vegetative", "days": (21, 35), "title": "Vegetative Growth (Days 21–35)", "tasks": "Keep field weed-free and check for iron chlorosis on young leaves in calcareous soils."},
            {"stage": "flowering", "days": (36, 65), "title": "Flowering & Pegging (Days 36–65)", "tasks": "Keep surface soil moist and loose so pegs penetrate easily; do not disturb soil after pegging starts."},
            {"stage": "fruiting", "days": (66, 95), "title": "Pod Development (Days 66–95)", "tasks": "Calcium and sulphur in the pegging zone are crucial for well-filled pods."},
            {"stage": "maturity", "days": (96, 115), "title": "Harvest & Curing (Days 96+)", "tasks": "Harvest when inner shell turns dark and dry pods thoroughly to safe moisture (<8%)."},
        ],
    },
    "soybean": {
        "name": "Soybean", "ph": (6.0, 7.0), "salt": "moderately tolerant",
        "heat_tmax": 35, "cold_tmin": 10, "duration_days": 100,
        "fym_tonnes_per_acre": (4, 5),
        "common_diseases": [],
        "heat_note": "Heat above about 35°C during flowering and pod filling reduces soybean yield.",
        "stages": [],
    },
    "grape": {
        "name": "Grape", "ph": (6.0, 7.5), "salt": "moderately sensitive",
        "heat_tmax": 40, "cold_tmin": 5, "duration_days": 140,
        "fym_tonnes_per_acre": (10, 12),
        "common_diseases": ["black_rot", "leaf_blight", "esca"],
        "heat_note": "Extreme heat (above about 40°C) can sunburn grape bunches.",
        "stages": [],
    },
    "apple": {
        "name": "Apple", "ph": (6.0, 7.0), "salt": "sensitive",
        "heat_tmax": 35, "cold_tmin": -5, "duration_days": 150,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["apple_scab", "black_rot", "cedar_apple_rust"],
        "heat_note": "High temperatures above about 35°C can cause sunburn on apple fruits.",
        "stages": [],
    },
    "orange": {
        "name": "Orange / Citrus", "ph": (6.0, 7.5), "salt": "sensitive",
        "heat_tmax": 38, "cold_tmin": 5, "duration_days": 180,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["citrus_greening"],
        "heat_note": "Extreme heat and dry winds during fruit set increase citrus fruit drop.",
        "stages": [],
    },
    "peach": {
        "name": "Peach", "ph": (6.0, 7.0), "salt": "sensitive",
        "heat_tmax": 35, "cold_tmin": 0, "duration_days": 130,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["bacterial_spot"],
        "heat_note": "Warm, wet weather favors bacterial spot on peach leaves and fruit.",
        "stages": [],
    },
    "strawberry": {
        "name": "Strawberry", "ph": (5.5, 6.5), "salt": "sensitive",
        "heat_tmax": 30, "cold_tmin": 2, "duration_days": 110,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["leaf_scorch"],
        "heat_note": "High temperatures above 30°C reduce fruit size and sweetness in strawberry.",
        "stages": [],
    },
    "squash": {
        "name": "Squash / Cucurbit", "ph": (6.0, 6.8), "salt": "moderately sensitive",
        "heat_tmax": 36, "cold_tmin": 12, "duration_days": 85,
        "fym_tonnes_per_acre": (6, 8),
        "common_diseases": ["powdery_mildew"],
        "heat_note": "High heat (>36°C) increases male flower ratio and reduces fruit set in cucurbits.",
        "stages": [],
    },
    "cherry": {
        "name": "Cherry", "ph": (6.0, 7.0), "salt": "sensitive",
        "heat_tmax": 33, "cold_tmin": -2, "duration_days": 120,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": ["powdery_mildew"],
        "heat_note": "Rain near harvest causes fruit cracking and disease in cherry.",
        "stages": [],
    },
    "blueberry": {
        "name": "Blueberry", "ph": (4.5, 5.5), "salt": "sensitive",
        "heat_tmax": 32, "cold_tmin": 0, "duration_days": 120,
        "fym_tonnes_per_acre": (6, 8),
        "common_diseases": [],
        "heat_note": "Blueberry requires strongly acidic, well-mulched soil.",
        "stages": [],
    },
    "raspberry": {
        "name": "Raspberry", "ph": (5.6, 6.5), "salt": "sensitive",
        "heat_tmax": 32, "cold_tmin": 0, "duration_days": 120,
        "fym_tonnes_per_acre": (6, 8),
        "common_diseases": [],
        "heat_note": "Good air circulation and trellis support reduce cane and leaf diseases.",
        "stages": [],
    },

    # ------------------------------------------------------------------
    # Common Indian smallholder crops added for the "Start a New Farm"
    # planner (pulses, millets and vegetables). No image model for these.
    # pH / salt / temperature limits: FAO ECOCROP, ICAR crop institutes
    # (IIPR pulses, IIMR millets, IIVR vegetables) package-of-practices.
    # ------------------------------------------------------------------
    "red_gram": {
        "name": "Red Gram (Tur / Arhar)", "ph": (6.5, 7.5), "salt": "sensitive",
        "heat_tmax": 38, "cold_tmin": 10, "duration_days": 160,
        "fym_tonnes_per_acre": (2, 3),
        "common_diseases": [],
        "heat_note": "Red gram tolerates heat and dry spells well, but frost at flowering damages pods.",
        "stages": [
            {"stage": "seedling", "days": (0, 30), "title": "Emergence & Early Growth (Days 0–30)", "tasks": "Sow on ridges or raised beds so water drains away. Red gram roots rot in waterlogged soil. Keep the field weed-free."},
            {"stage": "vegetative", "days": (31, 80), "title": "Branching (Days 31–80)", "tasks": "Do 1–2 hand weedings or inter-cultivation. Slow early growth makes red gram easy to intercrop with a short crop like green gram."},
            {"stage": "flowering", "days": (81, 120), "title": "Flowering (Days 81–120)", "tasks": "Install pheromone traps and bird perches for pod borer. Give one irrigation if there is a long dry spell."},
            {"stage": "fruiting", "days": (121, 150), "title": "Pod Filling (Days 121–150)", "tasks": "Check pods for borer holes twice a week. Avoid irrigation late in pod filling."},
            {"stage": "maturity", "days": (151, 180), "title": "Maturity & Harvest (Days 151+)", "tasks": "Harvest when about 80% of pods turn brown. Dry well before threshing and store in clean, dry bags."},
        ],
    },
    "green_gram": {
        "name": "Green Gram (Moong)", "ph": (6.2, 7.2), "salt": "moderately sensitive",
        "heat_tmax": 40, "cold_tmin": 15, "duration_days": 70,
        "fym_tonnes_per_acre": (2, 3),
        "common_diseases": [],
        "heat_note": "Green gram is a short, heat-tolerant crop but heavy rain at pod maturity causes pods to sprout.",
        "stages": [
            {"stage": "seedling", "days": (0, 15), "title": "Emergence (Days 0–15)", "tasks": "Treat seed with Rhizobium culture before sowing. Ensure good drainage."},
            {"stage": "vegetative", "days": (16, 30), "title": "Vegetative Growth (Days 16–30)", "tasks": "Hand weed once around day 20–25. Put up yellow sticky traps: whitefly spreads yellow mosaic virus."},
            {"stage": "flowering", "days": (31, 45), "title": "Flowering (Days 31–45)", "tasks": "Give a light irrigation if soil is dry. Pull out plants with yellow mosaic patches early."},
            {"stage": "fruiting", "days": (46, 60), "title": "Pod Development (Days 46–60)", "tasks": "Watch for pod borers and sucking pests."},
            {"stage": "maturity", "days": (61, 75), "title": "Picking & Harvest (Days 61+)", "tasks": "Pick mature black pods in 2–3 rounds before they shatter. Dry pods in the sun before threshing."},
        ],
    },
    "black_gram": {
        "name": "Black Gram (Urad)", "ph": (6.5, 7.5), "salt": "sensitive",
        "heat_tmax": 38, "cold_tmin": 15, "duration_days": 80,
        "fym_tonnes_per_acre": (2, 3),
        "common_diseases": [],
        "heat_note": "Black gram needs warm weather; waterlogging and very heavy rain at flowering reduce yield.",
        "stages": [
            {"stage": "seedling", "days": (0, 15), "title": "Emergence (Days 0–15)", "tasks": "Treat seed with Rhizobium culture. Sow in well-drained soil."},
            {"stage": "vegetative", "days": (16, 35), "title": "Vegetative Growth (Days 16–35)", "tasks": "Weed once around day 20–25. Use yellow sticky traps for whitefly (yellow mosaic virus carrier)."},
            {"stage": "flowering", "days": (36, 50), "title": "Flowering (Days 36–50)", "tasks": "Avoid water stress at flowering. Remove virus-infected plants."},
            {"stage": "fruiting", "days": (51, 70), "title": "Pod Development (Days 51–70)", "tasks": "Scout for pod borers."},
            {"stage": "maturity", "days": (71, 85), "title": "Harvest (Days 71+)", "tasks": "Harvest when most pods turn black. Dry and thresh; store in dry conditions."},
        ],
    },
    "chickpea": {
        "name": "Chickpea (Bengal Gram / Chana)", "ph": (6.0, 8.0), "salt": "sensitive",
        "heat_tmax": 32, "cold_tmin": 5, "duration_days": 110,
        "fym_tonnes_per_acre": (2, 3),
        "common_diseases": [],
        "heat_note": "Chickpea is a cool-season crop; temperatures above about 32°C at podding cause flower and pod drop.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Emergence (Days 0–20)", "tasks": "Sow on residual soil moisture after the rains. Treat seed with Rhizobium and Trichoderma to reduce wilt."},
            {"stage": "vegetative", "days": (21, 45), "title": "Branching (Days 21–45)", "tasks": "Weed once. Nipping the growing tips around day 30–40 encourages more branches (common practice)."},
            {"stage": "flowering", "days": (46, 75), "title": "Flowering & Podding (Days 46–75)", "tasks": "Install pheromone traps and bird perches for pod borer. If irrigated, give one light irrigation; avoid heavy watering."},
            {"stage": "fruiting", "days": (76, 95), "title": "Pod Filling (Days 76–95)", "tasks": "Check plants for pod borer larvae twice a week."},
            {"stage": "maturity", "days": (96, 115), "title": "Maturity & Harvest (Days 96+)", "tasks": "Harvest when leaves turn reddish-brown and dry. Dry seed well before storage."},
        ],
    },
    "onion": {
        "name": "Onion", "ph": (6.0, 7.0), "salt": "sensitive",
        "heat_tmax": 35, "cold_tmin": 10, "duration_days": 130,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": [],
        "heat_note": "Onion bulbs form best in mild weather; very hot weather at bulbing gives small bulbs.",
        "stages": [
            {"stage": "seedling", "days": (0, 45), "title": "Nursery & Transplanting (Days 0–45)", "tasks": "Raise seedlings on raised nursery beds. Transplant 6–7 week old seedlings."},
            {"stage": "vegetative", "days": (46, 75), "title": "Leaf Growth (Days 46–75)", "tasks": "Weed carefully (onion cannot compete with weeds). Use blue sticky traps to monitor thrips."},
            {"stage": "flowering", "days": (76, 105), "title": "Bulb Formation (Days 76–105)", "tasks": "Irrigate lightly and regularly. Water stress now gives small or split bulbs."},
            {"stage": "fruiting", "days": (106, 120), "title": "Bulb Maturity (Days 106–120)", "tasks": "Stop irrigation 10–15 days before harvest when tops start falling."},
            {"stage": "maturity", "days": (121, 140), "title": "Harvest & Curing (Days 121+)", "tasks": "Cure bulbs in shade for a week before storing in a well-ventilated place."},
        ],
    },
    "brinjal": {
        "name": "Brinjal (Eggplant)", "ph": (5.5, 6.8), "salt": "moderately sensitive",
        "heat_tmax": 37, "cold_tmin": 15, "duration_days": 150,
        "fym_tonnes_per_acre": (8, 10),
        "common_diseases": [],
        "heat_note": "Brinjal grows well in warm weather; frost or temperatures below about 15°C stop growth.",
        "stages": [
            {"stage": "seedling", "days": (0, 30), "title": "Nursery & Transplanting (Days 0–30)", "tasks": "Raise seedlings under insect-proof net. Transplant 4–5 week old seedlings."},
            {"stage": "vegetative", "days": (31, 55), "title": "Vegetative Growth (Days 31–55)", "tasks": "Weed and earth up. Install pheromone traps for shoot and fruit borer; cut and destroy wilted shoots."},
            {"stage": "flowering", "days": (56, 75), "title": "Flowering (Days 56–75)", "tasks": "Keep soil moist. Continue removing borer-damaged shoots."},
            {"stage": "fruiting", "days": (76, 130), "title": "Fruiting & Picking (Days 76–130)", "tasks": "Pick fruits every 4–6 days. Destroy bored fruits away from the field, do not leave them on the ground."},
            {"stage": "maturity", "days": (131, 160), "title": "Late Picking & Cleanup (Days 131+)", "tasks": "Remove and destroy old plants after the last picking to break the pest cycle."},
        ],
    },
    "okra": {
        "name": "Okra (Bhindi / Lady's Finger)", "ph": (6.0, 6.8), "salt": "moderately sensitive",
        "heat_tmax": 40, "cold_tmin": 15, "duration_days": 100,
        "fym_tonnes_per_acre": (6, 8),
        "common_diseases": [],
        "heat_note": "Okra needs warm soil to germinate and grows well in heat, but very cold nights stop growth.",
        "stages": [
            {"stage": "seedling", "days": (0, 15), "title": "Germination (Days 0–15)", "tasks": "Soak seed overnight before sowing for faster germination. Gap-fill missing spots."},
            {"stage": "vegetative", "days": (16, 35), "title": "Vegetative Growth (Days 16–35)", "tasks": "Weed twice. Put up yellow sticky traps: whitefly spreads yellow vein mosaic virus."},
            {"stage": "flowering", "days": (36, 45), "title": "Flowering (Days 36–45)", "tasks": "Irrigate regularly. Pull out plants with yellow-veined leaves early."},
            {"stage": "fruiting", "days": (46, 90), "title": "Fruiting & Picking (Days 46–90)", "tasks": "Pick tender pods every 2–3 days. Install pheromone traps for fruit borer."},
            {"stage": "maturity", "days": (91, 105), "title": "Final Picking (Days 91+)", "tasks": "Remove old plants after final picking."},
        ],
    },
    "jowar": {
        "name": "Jowar (Sorghum)", "ph": (6.0, 7.5), "salt": "moderately tolerant",
        "heat_tmax": 40, "cold_tmin": 12, "duration_days": 110,
        "fym_tonnes_per_acre": (4, 5),
        "common_diseases": [],
        "heat_note": "Jowar is drought-hardy and tolerates heat, making it suitable for rain-fed land.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Emergence (Days 0–25)", "tasks": "Sow early in the season; late sowing increases shoot fly damage. Thin to one healthy plant per spot."},
            {"stage": "vegetative", "days": (26, 55), "title": "Vegetative Growth (Days 26–55)", "tasks": "Weed and inter-cultivate. Watch whorls for stem borer damage."},
            {"stage": "flowering", "days": (56, 75), "title": "Flowering (Days 56–75)", "tasks": "Most sensitive to water stress now; give an irrigation if available."},
            {"stage": "fruiting", "days": (76, 100), "title": "Grain Filling (Days 76–100)", "tasks": "Protect earheads from birds near maturity."},
            {"stage": "maturity", "days": (101, 120), "title": "Harvest (Days 101+)", "tasks": "Harvest when grains are hard. Dry well; use stalks as fodder."},
        ],
    },
    "bajra": {
        "name": "Bajra (Pearl Millet)", "ph": (6.5, 7.5), "salt": "moderately tolerant",
        "heat_tmax": 42, "cold_tmin": 15, "duration_days": 85,
        "fym_tonnes_per_acre": (2, 4),
        "common_diseases": [],
        "heat_note": "Bajra is one of the most heat- and drought-tolerant cereals, suited to low-rainfall land.",
        "stages": [
            {"stage": "seedling", "days": (0, 20), "title": "Emergence (Days 0–20)", "tasks": "Sow with the onset of monsoon. Thin and gap-fill at 2–3 weeks."},
            {"stage": "vegetative", "days": (21, 40), "title": "Tillering (Days 21–40)", "tasks": "Weed once or twice. Remove plants showing downy mildew (green ear) symptoms."},
            {"stage": "flowering", "days": (41, 55), "title": "Flowering (Days 41–55)", "tasks": "Avoid water stress at flowering if irrigation is possible."},
            {"stage": "fruiting", "days": (56, 75), "title": "Grain Filling (Days 56–75)", "tasks": "Guard against birds as grains fill."},
            {"stage": "maturity", "days": (76, 90), "title": "Harvest (Days 76+)", "tasks": "Harvest earheads when grains are hard and dry."},
        ],
    },
    "ragi": {
        "name": "Ragi (Finger Millet)", "ph": (5.5, 7.5), "salt": "moderately tolerant",
        "heat_tmax": 35, "cold_tmin": 10, "duration_days": 115,
        "fym_tonnes_per_acre": (3, 4),
        "common_diseases": [],
        "heat_note": "Ragi is hardy and grows on poor, rain-fed soils; it stores very well after harvest.",
        "stages": [
            {"stage": "seedling", "days": (0, 25), "title": "Nursery / Emergence (Days 0–25)", "tasks": "Direct sow in lines or transplant 3–4 week old seedlings."},
            {"stage": "vegetative", "days": (26, 55), "title": "Tillering (Days 26–55)", "tasks": "Weed twice; ragi is slow at first and weeds compete strongly."},
            {"stage": "flowering", "days": (56, 80), "title": "Earhead Emergence & Flowering (Days 56–80)", "tasks": "Irrigate if there is a long dry spell. Watch for blast spots on leaves and neck."},
            {"stage": "fruiting", "days": (81, 100), "title": "Grain Filling (Days 81–100)", "tasks": "Protect from birds."},
            {"stage": "maturity", "days": (101, 120), "title": "Harvest (Days 101+)", "tasks": "Harvest earheads when they turn brown. Dry and thresh; grain stores for years if kept dry."},
        ],
    },
}

CROP_ALIASES = {
    "corn": "maize", "corn_(maize)": "maize", "maize": "maize", "maize_(corn)": "maize",
    "pepper,_bell": "pepper", "pepper_bell": "pepper", "bell_pepper": "pepper",
    "bell_pepper_/_capsicum": "pepper", "capsicum": "pepper", "pepper": "pepper",
    "paddy": "rice", "chili": "chilli", "chilli": "chilli",
    "peanut": "groundnut",
    "cherry_(including_sour)": "cherry",
    "orange_/_citrus": "orange", "citrus": "orange",
    "squash_/_cucurbit": "squash", "cucurbit": "squash",
    "tur": "red_gram", "arhar": "red_gram", "pigeonpea": "red_gram", "pigeon_pea": "red_gram", "redgram": "red_gram",
    "moong": "green_gram", "mung": "green_gram", "greengram": "green_gram",
    "urad": "black_gram", "blackgram": "black_gram",
    "gram": "chickpea", "chana": "chickpea", "bengal_gram": "chickpea",
    "eggplant": "brinjal", "baingan": "brinjal",
    "bhindi": "okra", "ladies_finger": "okra", "lady's_finger": "okra",
    "sorghum": "jowar", "pearl_millet": "bajra", "finger_millet": "ragi",
}

GROWTH_STAGES = ["seedling", "vegetative", "flowering", "fruiting", "maturity"]

SALT_SENSITIVE_CLASSES = {"sensitive", "moderately sensitive"}


def normalize_crop(name):
    if not name:
        return None
    raw = name.strip().lower()
    for k, prof in CROP_PROFILES.items():
        if prof["name"].lower() == raw:
            return k
    key = raw.replace(" ", "_")
    key = CROP_ALIASES.get(key, key)
    return key


def get_crop_profile(name):
    key = normalize_crop(name)
    if key and key in CROP_PROFILES:
        return key, CROP_PROFILES[key]
    return key, None
