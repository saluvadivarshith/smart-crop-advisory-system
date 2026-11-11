/**
 * Multilingual translation dictionary (English, Telugu, Hindi)
 * for the Smart Crop Advisory System.
 */

window.TRANSLATIONS = {
  en: {
    brand_sub: "Smart Crop Advisory for Small & Marginal Farmers",
    active_farm_label: "Selected Farm",
    nav_dashboard: "Dashboard",
    nav_farm: "Farm Profile & Location",
    nav_crop: "Crop Leaf Analysis",
    nav_soil: "Soil Health Card",
    nav_weather: "Farm Weather",
    nav_advisory: "Smart Advisory",
    nav_history: "Assessment History",
    helpline_label: "Kisan Call Centre (Toll-Free): 1800-180-1551",

    dash_title: "Farm Overview",
    dash_subtitle: "Live crop health, soil status, farm weather, and integrated risk",
    dash_metric_crop: "Selected Crop & Stage",
    dash_metric_disease: "Latest Leaf Check",
    dash_metric_soil: "Soil Health Score",
    dash_metric_risk: "Overall Crop Risk",
    dash_weather_title: "Current Farm Weather",
    dash_advisory_title: "Latest Farmer Advisory & Next Steps",
    dash_trend_title: "Historical Risk & Soil Health Trend",
    btn_run_full_advisory: "Generate & Save Full Advisory",
    btn_go_farm: "Set Farm Location",

    farm_title: "Farm Profile & Location",
    farm_subtitle: "Select your village/farm location and crop so weather and soil advice match your field",
    farm_locate_title: "1. Find Farm Location",
    btn_use_gps: "Use My Current GPS Location",
    btn_search_loc: "Search Village / Town",
    farm_details_title: "2. Farm & Crop Details",
    lbl_farm_name: "Farm Name / Plot Identifier",
    lbl_village: "Village / Town",
    lbl_district: "District",
    lbl_state: "State",
    lbl_lat: "Latitude",
    lbl_lon: "Longitude",
    lbl_crop: "Primary Crop",
    lbl_stage: "Current Growth Stage",
    lbl_area: "Farm Area (Acres, optional)",
    btn_save_farm: "Save Farm Profile",
    saved_farms_title: "Saved Farms",

    crop_title: "Crop Leaf Image Analysis",
    crop_subtitle: "Upload a close-up photograph of a crop leaf for ML disease screening",
    crop_upload_title: "Upload Leaf Photograph (JPG / PNG)",
    btn_analyze_crop: "Analyze Leaf Photo",
    crop_how_title: "Tips for a Clear Leaf Photo",
    tip_1: "Take the photo in natural daylight (avoid dark shadows or strong glare).",
    tip_2: "Fill the frame with a single affected leaf showing both spots and green margin.",
    tip_3: "Hold the phone steady so the leaf veins and spots are sharp, not blurry.",
    tip_4: "If the result is uncertain, inspect 10–15 nearby plants and consult your KVK.",

    soil_title: "Soil Health Card Analysis",
    soil_subtitle: "Enter values from your Government Soil Health Card (you can enter all 12 or only the ones you have)",
    btn_analyze_soil: "Analyze Soil Health",
    btn_fill_sample_deficient: "Load Sample Card (Low N & OC)",
    btn_fill_sample_healthy: "Load Sample Card (Balanced Soil)",
    btn_clear_soil: "Clear Values",

    weather_title: "Farm Weather Intelligence",
    weather_subtitle: "7-day Open-Meteo forecast, leaf-wetness hours, irrigation balance, and spray windows",
    btn_refresh_weather: "Refresh Farm Weather",
    weather_spray_title: "Recommended Spray / Field-Work Windows (Next 48h)",
    weather_irrigation_title: "3-Day Crop Water Balance (Rain vs. ET₀)",
    weather_forecast_title: "7-Day Agricultural Forecast",

    adv_title: "Integrated Risk & Farmer Advisory",
    adv_subtitle: "Explainable risk fusion combining leaf image, Soil Health Card, and 72-hour weather forecast",
    btn_speak_advisory: "Listen to Advisory (Audio)",
    btn_stop_audio: "Stop Audio",
    btn_copy_whatsapp: "Copy for WhatsApp / SMS",
    btn_print_report: "Print Advisory Card",

    hist_title: "Assessment History",
    hist_subtitle: "Saved crop assessments and historical trends stored in SQLite",
    btn_refresh_history: "Refresh History"
  },

  te: {
    brand_sub: "చిన్న మరియు సన్నకారు రైతుల కోసం స్మార్ట్ పంట సలహా వ్యవస్థ",
    active_farm_label: "ఎంచుకున్న పొలం",
    nav_dashboard: "డాష్‌బోర్డ్ (ముఖ్య వివరములు)",
    nav_farm: "పొలం వివరాలు & స్థానం",
    nav_crop: "ఆకు చిత్ర విశ్లేషణ (పంట వ్యాధి)",
    nav_soil: "భూసార పరీక్ష కార్డు (Soil Card)",
    nav_weather: "పొలం వాతావరణం",
    nav_advisory: "రైతు సలహా & ప్రమాద అంచనా",
    nav_history: "గత పరీక్షల చరిత్ర",
    helpline_label: "కిసాన్ కాల్ సెంటర్ (టోల్-ఫ్రీ): 1800-180-1551",

    dash_title: "పొలం సమగ్ర సమాచారం",
    dash_subtitle: "పంట ఆరోగ్యం, భూసారం, వాతావరణం మరియు సమగ్ర ప్రమాద అంచనా",
    dash_metric_crop: "ఎంచుకున్న పంట & దశ",
    dash_metric_disease: "ఆకు పరీక్ష ఫలితం",
    dash_metric_soil: "భూసార స్కోరు",
    dash_metric_risk: "మొత్తం పంట ప్రమాద స్థాయి",
    dash_weather_title: "ప్రస్తుత పొలం వాతావరణం",
    dash_advisory_title: "తాజా రైతు సలహాలు & చేయవలసిన పనులు",
    dash_trend_title: "ప్రమాద స్థాయి & భూసార చరిత్ర గ్రాఫ్",
    btn_run_full_advisory: "పూర్తి సలహా రూపొందించి సేవ్ చేయండి",
    btn_go_farm: "పొలం స్థానం ఎంచుకోండి",

    farm_title: "పొలం వివరాలు & స్థానం",
    farm_subtitle: "మీ గ్రామం మరియు పంటను ఎంచుకోండి, తద్వారా మీ పొలానికి తగిన వాతావరణం మరియు సలహాలు అందుతాయి",
    farm_locate_title: "1. పొలం స్థానాన్ని గుర్తించండి",
    btn_use_gps: "నా ప్రస్తుత GPS స్థానం వాడండి",
    btn_search_loc: "గ్రామం / మండలం వెతకండి",
    farm_details_title: "2. పొలం & పంట వివరాలు",
    lbl_farm_name: "పొలం పేరు / గుర్తు",
    lbl_village: "గ్రామం / పట్టణం",
    lbl_district: "జిల్లా",
    lbl_state: "రాష్ట్రం",
    lbl_lat: "అక్షాంశం (Latitude)",
    lbl_lon: "రేఖాంశం (Longitude)",
    lbl_crop: "ప్రధాన పంట",
    lbl_stage: "పంట పెరుగుదల దశ",
    lbl_area: "విస్తీర్ణం (ఎకరాలు - ఐచ్ఛికం)",
    btn_save_farm: "పొలం వివరాలు సేవ్ చేయండి",
    saved_farms_title: "సేవ్ చేసిన పొలాలు",

    crop_title: "పంట ఆకు చిత్ర విశ్లేషణ",
    crop_subtitle: "వ్యాధి గుర్తింపు కోసం పంట ఆకు యొక్క స్పష్టమైన ఫోటోను అప్‌లోడ్ చేయండి",
    crop_upload_title: "ఆకు ఫోటోను ఎంచుకోండి (JPG / PNG)",
    btn_analyze_crop: "ఆకు ఫోటోను పరీక్షించండి",
    crop_how_title: "స్పష్టమైన ఫోటో కోసం సూచనలు",
    tip_1: "పగటి వెలుగులో ఫోటో తీయండి (నీడలు లేదా మెరుపు లేకుండా చూడండి).",
    tip_2: "ఒకే ఆకు స్పష్టంగా కనిపించేలా దగ్గరగా ఫోటో తీయండి.",
    tip_3: "ఫోటో మసకగా కాకుండా స్పష్టంగా ఉండేలా ఫోన్ స్థిరంగా పట్టుకోండి.",
    tip_4: "ఫలితం అనిశ్చితంగా ఉంటే, పక్కనున్న 10–15 మొక్కలను పరిశీలించి వ్యవసాయ అధికారిని సంప్రదించండి.",

    soil_title: "భూసార పరీక్ష కార్డు విశ్లేషణ (Soil Health Card)",
    soil_subtitle: "మీ భూసార పరీక్ష కార్డులోని విలువలను నమోదు చేయండి (అన్ని లేదా మీ వద్ద ఉన్న విలువలు)",
    btn_analyze_soil: "భూసారం పరీక్షించండి",
    btn_fill_sample_deficient: "ఉదాహరణ విలువలు (తక్కువ నత్రజని)",
    btn_fill_sample_healthy: "ఉదాహరణ విలువలు (మంచి భూసారం)",
    btn_clear_soil: "ఖాళీ చేయండి",

    weather_title: "పొలం వాతావరణ సమాచారం",
    weather_subtitle: "7-రోజుల వాతావరణ సూచన, తేమ గంటలు, నీటి అవసరం మరియు పిచికారీకి అనుకూల సమయం",
    btn_refresh_weather: "వాతావరణం తాజాకరించండి",
    weather_spray_title: "పిచికారీ / పొలం పనులకు అనుకూల సమయం (48 గంటల్లో)",
    weather_irrigation_title: "3-రోజుల నీటి బ్యాలెన్స్ (వర్షం vs ఆవిరి నష్టం)",
    weather_forecast_title: "7-రోజుల వ్యవసాయ వాతావరణ సూచన",

    adv_title: "సమగ్ర పంట ప్రమాద అంచనా & రైతు సలహా",
    adv_subtitle: "ఆకు పరీక్ష, భూసార కార్డు మరియు వాతావరణ ఆధారిత ఆచరణాత్మక సూచనలు",
    btn_speak_advisory: "సలహా వినండి (ఆడియో)",
    btn_stop_audio: "ఆడియో ఆపండి",
    btn_copy_whatsapp: "వాట్సాప్ / SMS కోసం కాపీ చేయండి",
    btn_print_report: "సలహా కార్డు ప్రింట్ చేయండి",

    hist_title: "గత పరీక్షల చరిత్ర",
    hist_subtitle: "డేటాబేస్‌లో సేవ్ చేయబడిన గత పంట పరీక్షల వివరాలు",
    btn_refresh_history: "చరిత్ర తాజాకరించండి"
  },

  hi: {
    brand_sub: "छोटे और सीमांत किसानों के लिए स्मार्ट फसल सलाहकार प्रणाली",
    active_farm_label: "चयनित खेत",
    nav_dashboard: "डैशबोर्ड (मुख्य सारांश)",
    nav_farm: "खेत प्रोफ़ाइल और स्थान",
    nav_crop: "पत्ती चित्र जांच (रोग पहचान)",
    nav_soil: "मृदा स्वास्थ्य कार्ड (Soil Card)",
    nav_weather: "खेत का मौसम",
    nav_advisory: "किसान सलाह और जोखिम",
    nav_history: "पिछली जांच का इतिहास",
    helpline_label: "किसान कॉल सेंटर (टोल-फ्री): 1800-180-1551",

    dash_title: "खेत का अवलोकन",
    dash_subtitle: "फसल स्वास्थ्य, मिट्टी की स्थिति, मौसम और एकीकृत जोखिम मूल्यांकन",
    dash_metric_crop: "चयनित फसल और अवस्था",
    dash_metric_disease: "पत्ती जांच परिणाम",
    dash_metric_soil: "मृदा स्वास्थ्य स्कोर",
    dash_metric_risk: "कुल फसल जोखिम स्तर",
    dash_weather_title: "वर्तमान खेत मौसम",
    dash_advisory_title: "नवीनतम किसान सलाह और अगले कदम",
    dash_trend_title: "जोखिम और मृदा स्वास्थ्य रुझान",
    btn_run_full_advisory: "पूरी सलाह बनाएं और सहेजें",
    btn_go_farm: "खेत का स्थान चुनें",

    farm_title: "खेत प्रोफ़ाइल और स्थान",
    farm_subtitle: "अपने गाँव और फसल का चयन करें ताकि मौसम और मिट्टी की सलाह आपके खेत के अनुसार हो",
    farm_locate_title: "1. खेत का स्थान खोजें",
    btn_use_gps: "मेरा वर्तमान GPS स्थान उपयोग करें",
    btn_search_loc: "गाँव / तहसील खोजें",
    farm_details_title: "2. खेत और फसल विवरण",
    lbl_farm_name: "खेत का नाम / पहचान",
    lbl_village: "गाँव / कस्बा",
    lbl_district: "ज़िला",
    lbl_state: "राज्य",
    lbl_lat: "अक्षांश (Latitude)",
    lbl_lon: "देशांतर (Longitude)",
    lbl_crop: "मुख्य फसल",
    lbl_stage: "फसल की अवस्था",
    lbl_area: "क्षेत्रफल (एकड़ - वैकल्पिक)",
    btn_save_farm: "खेत प्रोफ़ाइल सहेजें",
    saved_farms_title: "सहेजे गए खेत",

    crop_title: "फसल पत्ती चित्र विश्लेषण",
    crop_subtitle: "रोग की पहचान के लिए पत्ती की स्पष्ट फ़ोटो अपलोड करें",
    crop_upload_title: "पत्ती की फ़ोटो चुनें (JPG / PNG)",
    btn_analyze_crop: "पत्ती फ़ोटो की जांच करें",
    crop_how_title: "स्पष्ट फ़ोटो के लिए सुझाव",
    tip_1: "दिन के उजाले में फ़ोटो लें (तेज़ चमक या अंधेरे से बचें)।",
    tip_2: "एक प्रभावित पत्ती को पास से साफ़ पृष्ठभूमि पर खींचें।",
    tip_3: "फ़ोन को स्थिर रखें ताकि धब्बे साफ़ दिखें, धुंधले नहीं।",
    tip_4: "यदि परिणाम अनिश्चित हो, तो आस-पास के 10–15 पौधों की जांच करें और कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",

    soil_title: "मृदा स्वास्थ्य कार्ड विश्लेषण",
    soil_subtitle: "अपने सरकारी मृदा स्वास्थ्य कार्ड से मान दर्ज करें (सभी 12 या जो उपलब्ध हों)",
    btn_analyze_soil: "मिट्टी की जांच करें",
    btn_fill_sample_deficient: "उदाहरण मान (कम नाइट्रोजन)",
    btn_fill_sample_healthy: "उदाहरण मान (संतुलित मिट्टी)",
    btn_clear_soil: "साफ़ करें",

    weather_title: "खेत मौसम बुद्धिमत्ता",
    weather_subtitle: "7-दिन का पूर्वानुमान, नमी के घंटे, सिंचाई संतुलन और छिड़काव का उपयुक्त समय",
    btn_refresh_weather: "मौसम ताज़ा करें",
    weather_spray_title: "छिड़काव / खेत कार्य के लिए उपयुक्त समय (अगले 48 घंटे)",
    weather_irrigation_title: "3-दिन का जल संतुलन (वर्षा बनाम ET₀)",
    weather_forecast_title: "7-दिन का कृषि मौसम पूर्वानुमान",

    adv_title: "एकीकृत जोखिम और किसान सलाह",
    adv_subtitle: "पत्ती जांच, मृदा कार्ड और 72-घंटे के मौसम पूर्वानुमान पर आधारित व्यावहारिक सलाह",
    btn_speak_advisory: "सलाह सुनें (ऑडियो)",
    btn_stop_audio: "ऑडियो रोकें",
    btn_copy_whatsapp: "व्हाट्सएप / SMS के लिए कॉपी करें",
    btn_print_report: "सलाह कार्ड प्रिंट करें",

    hist_title: "मूल्यांकन इतिहास",
    hist_subtitle: "डेटाबेस में सहेजे गए पिछले फसल मूल्यांकन और रुझान",
    btn_refresh_history: "इतिहास ताज़ा करें"
  }
};

window.currentLang = localStorage.getItem("cropsense_lang") || "en";

window.t = function (key) {
  const dict = window.TRANSLATIONS[window.currentLang] || window.TRANSLATIONS.en;
  return dict[key] || window.TRANSLATIONS.en[key] || key;
};

window.applyLanguage = function (lang) {
  if (!window.TRANSLATIONS[lang]) lang = "en";
  window.currentLang = lang;
  localStorage.setItem("cropsense_lang", lang);

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      el.textContent = window.t(key);
    }
  });

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
};
