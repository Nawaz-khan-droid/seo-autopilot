CITY_LOCATION_MAP: dict[str, str] = {
    "mumbai": "Mumbai, Maharashtra, India",
    "navi mumbai": "Navi Mumbai, Maharashtra, India",
    "thane": "Thane, Maharashtra, India",
    "pune": "Pune, Maharashtra, India",
    "delhi": "Delhi, India",
    "new delhi": "New Delhi, Delhi, India",
    "gurgaon": "Gurugram, Haryana, India",
    "gurugram": "Gurugram, Haryana, India",
    "bengaluru": "Bengaluru, Karnataka, India",
    "bangalore": "Bengaluru, Karnataka, India",
    "hyderabad": "Hyderabad, Telangana, India",
    "chennai": "Chennai, Tamil Nadu, India",
    "kolkata": "Kolkata, West Bengal, India",
    "ahmedabad": "Ahmedabad, Gujarat, India",
    "surat": "Surat, Gujarat, India",
    "jaipur": "Jaipur, Rajasthan, India",
    "kochi": "Kochi, Kerala, India",
    "kozhikode": "Kozhikode, Kerala, India",
    "indore": "Indore, Madhya Pradesh, India",
    "lucknow": "Lucknow, Uttar Pradesh, India",
    "noida": "Noida, Uttar Pradesh, India",
    "ghaziabad": "Ghaziabad, Uttar Pradesh, India",
    "chandigarh": "Chandigarh, India",
    "nagpur": "Nagpur, Maharashtra, India",
    "mysuru": "Mysuru, Karnataka, India",
    "mysore": "Mysuru, Karnataka, India",
    "coimbatore": "Coimbatore, Tamil Nadu, India",
    "visakhapatnam": "Visakhapatnam, Andhra Pradesh, India",
    "vizag": "Visakhapatnam, Andhra Pradesh, India",
    "bhopal": "Bhopal, Madhya Pradesh, India",
    "patna": "Patna, Bihar, India",
    "vadodara": "Vadodara, Gujarat, India",
    "ludhiana": "Ludhiana, Punjab, India",
    "agra": "Agra, Uttar Pradesh, India",
    "nasik": "Nashik, Maharashtra, India",
    "nashik": "Nashik, Maharashtra, India",
    "ranchi": "Ranchi, Jharkhand, India",
    "guwahati": "Guwahati, Assam, India",
    "chandigarh": "Chandigarh, India",
    "goa": "Goa, India",
    "panaji": "Panaji, Goa, India",
}


def normalize_location(raw_location: str) -> str:
    if not raw_location or not raw_location.strip():
        return "India"
    cleaned = raw_location.strip().lower()
    if cleaned in CITY_LOCATION_MAP:
        return CITY_LOCATION_MAP[cleaned]
    if cleaned.rstrip(".").endswith("india"):
        return raw_location.strip()
    return f"{raw_location.strip()}, India"
