"""
Disease knowledge base.

For each disease the model can predict we store:
  * a simple description,
  * the weather conditions under which it spreads (used by the risk engine),
  * low-cost cultural / preventive actions.

IMPORTANT DESIGN RULE: this file never contains pesticide names, doses or
spray schedules. Chemical control must come from validated local guidance
(KVK / state agriculture department / labelled product instructions).

Weather "favourable" rules are simplified from plant-pathology literature:
  * Late blight – Hutton/Smith-period style rule: temperature >= 10°C with
    relative humidity >= 90% for many hours (Dancey et al. 2017, Plant
    Pathology 66:1000-1010; Fry 2008, Mol. Plant Pathol. 9:385-402).
  * Early blight – warm (about 20-30°C) with long leaf-wetness / high humidity
    (Chaerani & Voorrips 2006, J. Gen. Plant Pathol. 72:335-347).
  * Bacterial spot – warm (24-30°C), rain splash and high humidity
    (Potnis et al. 2015, Mol. Plant Pathol. 16:907-920).
  * Two-spotted spider mite – hot, dry weather favours rapid build-up
    (Van Leeuwen et al. 2010, Insect Biochem. Mol. Biol. 40:563-572).
  * Other diseases – standard extension fact sheets (APS, university
    extension services, ICAR-NCIPM).
A "favourable hour" is an hourly forecast record that meets the rule.
"""

# Each entry: keywords used to match model class names (first match wins,
# so more specific keywords appear first).
DISEASES = [
    {
        "key": "late_blight", "keywords": ["late_blight"],
        "name": "Late Blight", "type": "oomycete (water mould)", "urgency": "high",
        "about": "Dark, water-soaked patches on leaves that spread very fast in cool, wet weather. It can destroy a field within days.",
        "weather": {"temp_min": 10, "temp_max": 25, "rh_min": 90, "hours_high": 10, "hours_moderate": 5,
                    "text": "cool (10–25°C) and very humid (RH ≥ 90%) weather"},
        "actions": [
            "Remove and destroy infected leaves or plants right away. Do not leave them in the field or put them in compost.",
            "Do not water the leaves. Water at the base of the plant, in the morning, so leaves dry quickly.",
            "Check plants in the whole field and tell neighbouring farmers, because this disease spreads quickly through air.",
            "Contact your KVK or agriculture officer immediately for control advice for your crop.",
            "Next season, use certified disease-free seed or seedlings and resistant varieties if available.",
        ],
    },
    {
        "key": "early_blight", "keywords": ["early_blight"],
        "name": "Early Blight", "type": "fungal", "urgency": "moderate",
        "about": "Brown spots with ring-like circles ('target' pattern), usually first on older lower leaves.",
        "weather": {"temp_min": 20, "temp_max": 30, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm (20–30°C) and humid (RH ≥ 85%) weather with wet leaves"},
        "actions": [
            "Remove the affected lower leaves and destroy them away from the field.",
            "Put straw or dry leaf mulch around plants so soil does not splash onto leaves.",
            "Water at the base of the plant, not on the leaves.",
            "Keep the crop well-nourished. Weak and nutrient-stressed plants get early blight more easily.",
            "After harvest, remove crop residues. Do not grow tomato, potato, chilli or brinjal in the same place next season (crop rotation).",
        ],
    },
    {
        "key": "bacterial_spot", "keywords": ["bacterial_spot"],
        "name": "Bacterial Spot", "type": "bacterial", "urgency": "moderate",
        "about": "Small dark, greasy-looking spots on leaves and fruits. It spreads by rain splash and by handling wet plants.",
        "weather": {"temp_min": 24, "temp_max": 30, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm (24–30°C), humid weather with rain splash"},
        "actions": [
            "Do not work in the field or touch plants while leaves are wet.",
            "Remove badly affected leaves and destroy them.",
            "Avoid overhead watering. Water at the base of plants.",
            "Clean tools and hands after working with infected plants.",
            "Next season, use disease-free seed and healthy seedlings, and rotate crops.",
        ],
    },
    {
        "key": "leaf_mold", "keywords": ["leaf_mold", "leaf_mould"],
        "name": "Leaf Mold", "type": "fungal", "urgency": "moderate",
        "about": "Yellow patches on the upper leaf surface with olive-green or grey mould underneath. Common in dense, humid crops.",
        "weather": {"temp_min": 20, "temp_max": 25, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "mild (20–25°C) and very humid (RH ≥ 85%) conditions"},
        "actions": [
            "Improve air movement: remove some lower leaves and keep good spacing between plants.",
            "Remove and destroy affected leaves.",
            "Avoid wetting the leaves when watering.",
        ],
    },
    {
        "key": "septoria_leaf_spot", "keywords": ["septoria"],
        "name": "Septoria Leaf Spot", "type": "fungal", "urgency": "moderate",
        "about": "Many small round spots with grey centres and dark edges, starting on lower leaves.",
        "weather": {"temp_min": 20, "temp_max": 25, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "mild (20–25°C), wet and humid weather"},
        "actions": [
            "Remove the infected lower leaves and destroy them.",
            "Use mulch to stop soil splashing onto leaves.",
            "Water at the base of plants.",
            "Remove weeds of the tomato family around the field and rotate crops next season.",
        ],
    },
    {
        "key": "spider_mites", "keywords": ["spider_mite"],
        "name": "Spider Mites", "type": "pest (mite)", "urgency": "moderate",
        "about": "Tiny mites under the leaves cause fine yellow speckles and fine webbing. They multiply fast in hot, dry weather.",
        "weather": {"temp_min": 27, "temp_max": 45, "rh_max": 50, "hours_high": 24, "hours_moderate": 10,
                    "text": "hot (≥ 27°C) and dry (RH ≤ 50%) weather"},
        "actions": [
            "Check the underside of leaves with a hand lens for mites and webbing.",
            "Spraying plain water forcefully on the underside of leaves can knock mites off.",
            "Remove heavily infested leaves.",
            "Keep plants well-watered. Drought-stressed plants suffer more.",
            "Avoid unnecessary broad-spectrum sprays. They kill the natural enemies that eat mites.",
        ],
    },
    {
        "key": "target_spot", "keywords": ["target_spot"],
        "name": "Target Spot", "type": "fungal", "urgency": "moderate",
        "about": "Brown spots with light-coloured rings on leaves, which can also affect fruits.",
        "weather": {"temp_min": 20, "temp_max": 28, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm (20–28°C) and humid weather"},
        "actions": [
            "Remove affected lower leaves to improve air movement.",
            "Avoid wetting leaves while watering.",
            "Remove crop residues after harvest and rotate crops.",
        ],
    },
    {
        "key": "yellow_leaf_curl_virus", "keywords": ["yellow_leaf_curl", "yellowleaf_curl", "yellowleaf__curl"],
        "name": "Yellow Leaf Curl Virus", "type": "viral (spread by whitefly)", "urgency": "high",
        "about": "Leaves curl upward, become small and yellow, and plants stop growing. It is spread by whiteflies. Infected plants cannot be cured.",
        "weather": {"temp_min": 25, "temp_max": 35, "rh_max": 70, "hours_high": 30, "hours_moderate": 15,
                    "text": "warm and dry weather, which favours whitefly"},
        "actions": [
            "Pull out and destroy infected plants early, before whiteflies spread the virus to healthy plants.",
            "Use yellow sticky traps to monitor and reduce whiteflies. They are low cost.",
            "Remove weeds around the field that host whiteflies.",
            "Raise seedlings under insect-proof net, and use resistant varieties next season.",
            "Ask your KVK about whitefly management for your area.",
        ],
    },
    {
        "key": "mosaic_virus", "keywords": ["mosaic_virus", "mosaic"],
        "name": "Mosaic Virus", "type": "viral", "urgency": "high",
        "about": "Light and dark green mottled (mosaic) pattern on leaves, with distorted growth. It spreads through hands, tools and infected seed. It cannot be cured.",
        "weather": None,
        "actions": [
            "Remove and destroy infected plants.",
            "Wash hands and clean tools after touching infected plants.",
            "Do not smoke or handle tobacco while working with plants, because tobacco can carry related viruses.",
            "Use clean, certified seed and resistant varieties next season.",
        ],
    },
    {
        "key": "powdery_mildew", "keywords": ["powdery_mildew"],
        "name": "Powdery Mildew", "type": "fungal", "urgency": "moderate",
        "about": "White powdery patches on leaves. Unlike most fungal diseases, it does not need rain and spreads in humid air with dry leaves.",
        "weather": {"temp_min": 20, "temp_max": 27, "rh_min": 60, "hours_high": 30, "hours_moderate": 15,
                    "text": "moderate temperatures (20–27°C) with humid air"},
        "actions": [
            "Remove and destroy heavily affected leaves.",
            "Improve air movement with proper spacing and pruning.",
            "Avoid applying too much nitrogen, which produces soft leaves that are more susceptible.",
        ],
    },
    {
        "key": "common_rust", "keywords": ["common_rust"],
        "name": "Common Rust", "type": "fungal", "urgency": "low",
        "about": "Small reddish-brown powdery pustules on both sides of maize leaves.",
        "weather": {"temp_min": 16, "temp_max": 25, "rh_min": 95, "hours_high": 8, "hours_moderate": 4,
                    "text": "cool (16–25°C) weather with heavy dew (RH ≥ 95%)"},
        "actions": [
            "Monitor how fast the pustules increase. Mild infection late in the season usually causes little loss.",
            "Choose resistant hybrids in the next season.",
            "Ask your agriculture officer if infection is heavy before flowering.",
        ],
    },
    {
        "key": "northern_leaf_blight", "keywords": ["northern_leaf_blight"],
        "name": "Northern Leaf Blight", "type": "fungal", "urgency": "moderate",
        "about": "Long, cigar-shaped grey-green to tan lesions on maize leaves.",
        "weather": {"temp_min": 18, "temp_max": 27, "rh_min": 90, "hours_high": 10, "hours_moderate": 5,
                    "text": "moderate temperatures (18–27°C) with long dew periods"},
        "actions": [
            "Monitor whether lesions spread to upper leaves before flowering.",
            "After harvest, manage crop residue and rotate with a non-cereal crop.",
            "Use resistant hybrids next season.",
        ],
    },
    {
        "key": "gray_leaf_spot", "keywords": ["gray_leaf_spot", "cercospora"],
        "name": "Gray Leaf Spot", "type": "fungal", "urgency": "moderate",
        "about": "Rectangular grey to tan lesions between leaf veins of maize.",
        "weather": {"temp_min": 22, "temp_max": 30, "rh_min": 90, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm (22–30°C), very humid weather"},
        "actions": [
            "Rotate maize with other crops and manage residues after harvest.",
            "Use tolerant hybrids next season.",
            "Ask your agriculture officer if lesions reach upper leaves before grain filling.",
        ],
    },
    {
        "key": "apple_scab", "keywords": ["apple_scab", "scab"],
        "name": "Apple Scab", "type": "fungal", "urgency": "moderate",
        "about": "Olive-green to black velvety spots on leaves and fruits.",
        "weather": {"temp_min": 13, "temp_max": 24, "rh_min": 90, "hours_high": 10, "hours_moderate": 6,
                    "text": "cool, wet weather with long leaf wetness"},
        "actions": [
            "Collect and destroy fallen infected leaves.",
            "Prune to open the canopy for better air movement.",
            "Ask your horticulture officer for scab management advice.",
        ],
    },
    {
        "key": "cedar_apple_rust", "keywords": ["cedar_apple_rust"],
        "name": "Cedar Apple Rust", "type": "fungal", "urgency": "low",
        "about": "Bright orange-yellow spots on apple leaves. The fungus alternates between apple and juniper/cedar trees.",
        "weather": {"temp_min": 13, "temp_max": 24, "rh_min": 90, "hours_high": 8, "hours_moderate": 4,
                    "text": "mild, wet weather"},
        "actions": [
            "Remove nearby juniper or cedar hosts where practical.",
            "Use resistant varieties for new plantings.",
        ],
    },
    {
        "key": "black_rot", "keywords": ["black_rot"],
        "name": "Black Rot", "type": "fungal", "urgency": "moderate",
        "about": "Brown leaf spots and shrivelled, black, mummified fruits.",
        "weather": {"temp_min": 20, "temp_max": 30, "rh_min": 90, "hours_high": 10, "hours_moderate": 6,
                    "text": "warm, wet weather"},
        "actions": [
            "Remove mummified fruits and infected parts and destroy them.",
            "Prune to improve air flow in the canopy.",
            "Ask your horticulture officer for management advice.",
        ],
    },
    {
        "key": "esca", "keywords": ["esca", "black_measles"],
        "name": "Esca (Black Measles)", "type": "fungal (trunk disease)", "urgency": "moderate",
        "about": "Striped, 'tiger-stripe' leaf discolouration and spotted berries, caused by fungi inside the wood.",
        "weather": None,
        "actions": [
            "Cut out and destroy infected wood.",
            "Prune in dry weather and protect large pruning wounds.",
            "Avoid stressing vines through poor water and nutrient management.",
        ],
    },
    {
        "key": "leaf_blight", "keywords": ["leaf_blight", "isariopsis"],
        "name": "Leaf Blight", "type": "fungal", "urgency": "moderate",
        "about": "Irregular dark brown spots that join together and dry the leaf.",
        "weather": {"temp_min": 25, "temp_max": 30, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm, humid weather"},
        "actions": [
            "Remove and destroy affected leaves.",
            "Improve air movement through pruning and canopy management.",
        ],
    },
    {
        "key": "citrus_greening", "keywords": ["haunglongbing", "huanglongbing", "greening"],
        "name": "Citrus Greening (HLB)", "type": "bacterial (spread by psyllid insect)", "urgency": "high",
        "about": "Blotchy yellow leaves, small lopsided bitter fruits. It is spread by the citrus psyllid. There is no cure.",
        "weather": None,
        "actions": [
            "Get the diagnosis confirmed by your horticulture department.",
            "Infected trees usually need to be removed to protect the rest of the orchard.",
            "Monitor and manage citrus psyllid. Use only certified disease-free planting material.",
        ],
    },
    {
        "key": "leaf_scorch", "keywords": ["leaf_scorch"],
        "name": "Leaf Scorch", "type": "fungal", "urgency": "low",
        "about": "Many small purple spots that merge, making leaves look scorched.",
        "weather": {"temp_min": 20, "temp_max": 27, "rh_min": 85, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm, wet weather"},
        "actions": [
            "Remove infected leaves.",
            "Avoid overhead watering.",
            "Renovate old beds and use healthy planting material.",
        ],
    },
]

# Generic fall-backs when a disease name is not in the list above.
GENERIC_BY_TYPE = {
    "fungal": {
        "weather": {"temp_min": 18, "temp_max": 30, "rh_min": 90, "hours_high": 12, "hours_moderate": 6,
                    "text": "warm and very humid weather"},
        "actions": [
            "Remove and destroy affected leaves.",
            "Avoid wetting leaves while watering, and improve air movement.",
            "Ask your KVK or agriculture officer to confirm the disease.",
        ],
    },
}

DISEASE_BY_KEY = {d["key"]: d for d in DISEASES}


def find_disease(slug):
    """Find the knowledge-base entry that matches a model class slug."""
    if not slug:
        return None
    s = slug.lower()
    for entry in DISEASES:
        if any(k in s for k in entry["keywords"]):
            return entry
    return None
