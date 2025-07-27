import requests
import json
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from google import genai
from google.genai import types

load_dotenv()
app = FastAPI()
origins = [
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAPS_API_KEY = os.getenv("MAPS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class Cafe(BaseModel):
    name: str
    address: str

class CafeListRequest(BaseModel):
    data: list[Cafe]

class Photo(BaseModel):
    url: str
    authorName: str
    authorURL: str

class Details(BaseModel):
    servesBreakfast: bool | None = False
    servesLunch: bool | None = False
    servesDinner: bool | None = False
    servesBrunch: bool | None = False
    outdoorSeating: bool | None = False
    liveMusic: bool | None = False
    servesDessert: bool | None = False
    servesCoffee: bool | None = False
    goodForChildren: bool | None = False
    allowsDogs: bool | None = False
    restroom: bool | None = False
    goodForGroups: bool | None = False
    parkingOptions: dict = {}
    paymentMethods: dict = {}

class Place(BaseModel):
    name: str
    address: str
    rating: float | None = None
    total_ratings: int | None = None
    googleMapsURL: str | None = None
    websiteURL: str | None = None
    regularOpeningHours: list[str] = []
    photo: Photo
    priceRange: dict = {}
    accessibilityOptions: dict = {}
    details: Details
    reviews: list[str] = []
    landmarks: list[str] = []

class PlaceListRequest(BaseModel):
    places: list[Place]

results = []
@app.get("/nearby-places")
async def root(lat: float = -7.770682552597794, lon: float = 110.3588946, radius: int = 1000):
    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': MAPS_API_KEY,
        'X-Goog-FieldMask': "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri,places.websiteUri,places.regularOpeningHours,places.photos,places.priceRange,places.accessibilityOptions,places.servesBreakfast,places.servesLunch,places.servesDinner,places.servesBrunch,places.outdoorSeating,places.liveMusic,places.servesDessert,places.servesCoffee,places.goodForChildren,places.restroom,places.parkingOptions,places.paymentOptions,places.reviews,places.addressDescriptor.landmarks"
    }
    payload = {
        "includedTypes": ["cafe", "coffee_shop"],
        "excludedPrimaryTypes": ["restaurant", "bar", "store"], 
        "languageCode": "id",
        "maxResultCount": 5,
        "rankPreference": "POPULARITY",
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": radius
            }
        }
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        places_result = response.json()

        for place in places_result.get('places', []):
            photo_url = "No photo available"
            author_name = "N/A"
            author_url = "N/A"

            if place.get('photos') and len(place['photos']) > 0:
                photo_ref = place['photos'][0]['name'].split('/')[-1]
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={MAPS_API_KEY}"
                
                if place['photos'][0].get('authorAttributions') and len(place['photos'][0]['authorAttributions']) > 0:
                    author_name = place['photos'][0]['authorAttributions'][0].get('displayName', 'N/A')
                    author_url = place['photos'][0]['authorAttributions'][0].get('uri', 'N/A')

            place_data = Place(
                name=place.get('displayName', {}).get('text', 'N/A'),
                address=place.get('formattedAddress', 'N/A'),
                rating=place.get('rating'),
                total_ratings=place.get('userRatingCount'),
                googleMapsURL=place.get('googleMapsUri'),
                websiteURL=place.get('websiteUri'),
                regularOpeningHours=place.get('regularOpeningHours', {}).get('weekdayDescriptions', []),
                photo=Photo(url=photo_url, authorName=author_name, authorURL=author_url),
                priceRange=place.get('priceRange', {}),
                accessibilityOptions=place.get('accessibilityOptions', {}),
                details=Details(
                    servesBreakfast=place.get('servesBreakfast'),
                    servesLunch=place.get('servesLunch'),
                    servesDinner=place.get('servesDinner'),
                    servesBrunch=place.get('servesBrunch'),
                    outdoorSeating=place.get('outdoorSeating'),
                    liveMusic=place.get('liveMusic'),
                    servesDessert=place.get('servesDessert'),
                    servesCoffee=place.get('servesCoffee'),
                    goodForChildren=place.get('goodForChildren'),
                    restroom=place.get('restroom'),
                    parkingOptions=place.get('parkingOptions', {}),
                    paymentMethods=place.get('paymentOptions', {})
                ),
                reviews=[review.get('originalText', {}).get('text', '') for review in place.get('reviews', [])],
                landmarks=list(set(
                    landmark_type for landmark in place.get('addressDescriptor', {}).get('landmarks', []) 
                    for landmark_type in landmark.get('types', [])
                ))
            )
            results.append(place_data)
            # print(results)
        
        
        analysis_results = await get_cafe_feature(results)
        return JSONResponse(content=jsonable_encoder(analysis_results))

    except requests.exceptions.RequestException as e:
        error_msg = {"error": "Google Maps API Error", "details": str(e)}
        return JSONResponse(content=jsonable_encoder(error_msg), status_code=500)
    except Exception as e:
        error_msg = {"error": "An unexpected server error occurred", "details": str(e)}
        return JSONResponse(content=jsonable_encoder(error_msg), status_code=500)

async def get_cafe_feature(cafe: list):
    client = genai.Client(api_key=GEMINI_API_KEY)

    # instruction = f"""
    # Tugas Anda adalah menganalisis daftar kafe berdasarkan informasi yang tersedia dari Google Maps. Untuk setiap kafe, hasilkan satu objek JSON lengkap berdasarkan format yang telah ditentukan.

    # PETUNJUK PENTING:
    # 1. Hasilkan satu objek JSON untuk setiap kafe, tulis setiap objek pada satu baris.
    # 2. Pastikan setiap field dalam objek JSON terisi secara lengkap dengan format yang sesuai (boolean, string, atau array of string).

    # CONTOH FORMAT OUTPUT (per objek JSON):
    # {{
    # "cafe_name": "Fore Coffee",
    # "address": "Jl. Raya Condong Catur No. 1, Condong Catur, Sleman, Yogyakarta",
    # "atmosphere": {{ "indoor": true, "outdoor": true }},
    # "menu": {{ "tea": false, "coffee": true, "snack": true, "rice": false }},
    # "facility": {{ "wifi": true, "electricity": true, "mushala": false, "toilet": true, "parking_area": true }},
    # "payment": {{ "cash": true, "nonCash": true }},
    # "recommendedMenu": ["Butterscotch Sea Salt Latte", "Pain au Chocolat"],
    # "conclusion": "WFC friendly (pilih antara WFC friendly | Hangout with friend | Hangout with family)",
    # "landmark": {{ "atm": true, "hospital": false, "mall": true, "mosque": true, "minimarket": true }},
    # }}
    # """

    instruction = f"""
    Tugas Anda adalah menganalisis daftar kafe berdasarkan informasi yang tersedia dari Google Maps dan mengembalikan hasilnya dalam satu array JSON tunggal.

    PETUNJUK PENTING:
    1. Hasilkan satu array JSON (`[]`) yang berisi objek untuk SEMUA kafe yang dianalisis.
    2. Jangan di-stream. Seluruh respons harus berupa satu blok JSON yang valid.
    3. Pastikan setiap field dalam objek JSON terisi secara lengkap.
    4. Gunakan format yang telah ditentukan untuk setiap objek JSON.

    CONTOH FORMAT OUTPUT (Keseluruhan Respons):
    [
        {{
            "cafe_name": "Fore Coffee",
            "rating": 4.5,
            "address": "Jl. Raya Condong Catur...",
            "atmosphere": {{ "indoor": true, "outdoor": true }},
            "photo": {{
                "url": "https://example.com/photo.jpg",
                "author_name": "John Doe",
                "author_url": "https://example.com/author"
            }},
            "google_maps_url": "https://maps.google.com/?cid=1234567890",
            "price_range": "25.000 - 50.000 IDR",
            "menu": {{ "coffee": true, "nonCoffee": true, "snack": true, "rice": false }},
            "facility": {{ "wifi": true, "electricity": true, "mushala": false, "kids_friendly": true, "accessible": false }},
            "payment": {{ "cash": true, "non_cash": true }},
            "recommended_menu": ["Butterscotch Sea Salt Latte", "Pain au Chocolat"],
            "conclusion": "pilih satu di antara kategori berikut:
            WFC friendly | Hangout with friend | Hangout with family",
            "landmark": {{ "atm": true, "rumah_sakit": false, "mall": true, "masjid": true, "minimarket": true }}
        }}
    ]
    """

    prompt = f"""
    ### DATA KAFE UNTUK DIANALISIS:
    {cafe}
    """

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.4,
            top_p=0.8,
        ),
        contents=prompt
    )

    try:
        full_text = response.candidates[0].content.parts[0].text

        cleaned_text = full_text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[7:].strip()
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3].strip()

        results = json.loads(cleaned_text)
        return results
        
    except (IndexError, AttributeError, json.JSONDecodeError) as e:
        print(f"Error processing the Gemini response: {e}")
        return []

@app.post("/analyze")
async def analyze_cafes_stream_endpoint(request: PlaceListRequest):
    return StreamingResponse(
        get_cafe_feature(request.places),
        media_type="application/x-json-stream"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)