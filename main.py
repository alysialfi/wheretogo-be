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
        
        # results = [Place(name='Space Roastery HQ', address='Gg. Loncang No.88, Rogoyudan, Sinduadi, Kec. Mlati, Kabupaten Sleman, Daerah Istimewa Yogyakarta 55284, Indonesia', rating=4.7, total_ratings=1276, googleMapsURL='https://maps.google.com/?cid=10520739776554691999&g_mp=Cilnb29nbGUubWFwcy5wbGFjZXMudjEuUGxhY2VzLlNlYXJjaE5lYXJieRAAGAQgAA', websiteURL='https://www.spaceroastery.com/', regularOpeningHours=['Senin: 07.00–00.00', 'Selasa: 07.00–00.00', 'Rabu: 07.00–00.00', 'Kamis: 07.00–00.00', 'Jumat: 07.00–00.00', 'Sabtu: 07.00–00.00', 'Minggu: 07.00–00.00'], photo=Photo(url='https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=ATKogpeQYLB_y9Np7KOIVYg9aUlKNW80Fw1yMUQDmN8-JQnEkdm_hdKYneWM96UsgdHeX0K2UxHABOlCvo_NVm32R0Lp-7Hc4ZLIWZeOO_bHeksvw7GusG_lptHfupISyiMYVLZdcOqIRq8Y6j7RNhFW4LoW4UslqwzgjBtC_5GQgdp0tWlJQPBgpH1Urxr6OwigdnAI_t9qe9OpQawNOYzApJNFexX2aVOC44qMw8wHETN9Qh9sVO_L2bsCray92IDlPJQrgmyT3MilfATdYIiOz78mDJzOVhNdedxE7wVBdIgLGQ&key=AIzaSyByX6zAtiVo9qYDr46kswF828RfopoJL68', authorName='Space Roastery HQ', authorURL='https://maps.google.com/maps/contrib/109443540979177576959'), priceRange={'startPrice': {'currencyCode': 'IDR', 'units': '25000'}, 'endPrice': {'currencyCode': 'IDR', 'units': '50000'}}, accessibilityOptions={'wheelchairAccessibleEntrance': False}, details=Details(servesBreakfast=None, servesLunch=None, servesDinner=None, servesBrunch=None, outdoorSeating=None, liveMusic=None, servesDessert=None, servesCoffee=None, goodForChildren=None, allowsDogs=False, restroom=None, goodForGroups=False, parkingOptions={'freeParkingLot': True, 'paidParkingLot': True, 'paidStreetParking': True}, paymentMethods={'acceptsCreditCards': True, 'acceptsDebitCards': True, 'acceptsCashOnly': False, 'acceptsNfc': True}), reviews=['Aku yg senang kopi manual brew, tujuanku di jogja kesini salah satunya. Roastery legend yg aku tau bertahan sampai sekarang dari aku mulai nyari kopi 2015. Banyak varian beansnya, dan semua ada testernya dlm insulated server bisa di icip. Kalau aku favorit halu pink banana dgn apple cider..', 'Tempatnya cendrung kotor ya, dilantai banyak bekas abu rokok padalah diruang non-smoking. Mungkin saat kami berkujung masih kepagian.\n\nKopinya memang serius dan cocok untuk yang lagi eksplore kopi jogja, untuk temen2 yang mentoknya doyan es kopi susu disarankan untuk cek menu dulu, apajag ada yang bisa dipese.\n\nCrew bar ramah dan baik, walopun kasir lumayan kagok jelasin produknya.', 'Beans nya jelas enak2, kopinya (harusnya) enak, sayangnya hari ini saya dapat ga enak. Barista please serve your best coffee. Kesini karena mau ngopi enak malah zonk, foamnya pecah, udah dingin dan rasanya kurang keluar. Originote dan strawberry fields harusnya bisa lebih enak dari hari ini. Tolong sedia piring & cutlery untuk cookies yg akan dihangatkan untuk dine in, karena tadi cookies saya langsung dimasukkan ke microwave bersama paperbagnya (???? wow speechless). Mbak kasir, karena sedang dalam posisi bekerja sebaiknya bisa lebih mengontrol attitude ya. Lebih sopan dan kalem akan lebih menyenangkan. Sekian, semoga ini cuma different shit in different day. Semangat space!', 'Minuman\nAku coba minuman yang banyak orang rekomendasiin geisha sama voodoo. Geisha itu rasanya kaya teh tarik ga tau kopinya dimana ga berasa 😭 dan voodoo ya kaya matcha latte biasa aja juga. Mungkin kalau kesana lagi mau coba menu lain sih.\n\nHarga\nStandar kopi pada umumnya sih 2 kaleng tu habis 60k\n\nPelayanan\nCukup ramah si kakak kakak nya.\n\nTempat\nTidak terlalu luas smoking nya outdoor indoor nya non. Colokanya banyakan yang di outdoor sedangkan kalau kesana siang ya panas bgt say. Mau ga mau ya di indoor dan ga terlalu luas colokanya jg dikit. Mau colok aja harus join sama meja lain 😭. Maaf buat mas yang saya repotin jadi sharing meja dan terimakasih banget boleh sharing meja. Untung mas nya juga ramah dan welcome 😁. Hitung hitung tambah interaksi dengan manusia lain hihi.', 'Salah satu kopi roaster yang terkenal di Indonesia. Akhirnya nyoba langsung ke kedai kopi nya. Tempatnya masuk gang, bukan yang di jalan raya, tapi tempatnya lumayan juga.\n\nNyoba split shot nya. Espresso nya enak. Dominan acid, tapi ada after taste agak manis. Espresso based nya juga enak.\n\nMenu yang terkenal dari sini sih beans kopi halu banana nya. Buat yang suka kopi, bisa dicoba langsung sih, recommend banget buat yang suka kopi.'], landmarks=['finance', 'store', 'establishment', 'bank', 'food', 'point_of_interest', 'electronics_store', 'restaurant']), Place(name='Fordo Coffee Lab', address='Jl. Magelang Kidul No.442, Karangwaru, Kec. Tegalrejo, Kota Yogyakarta, Daerah Istimewa Yogyakarta 55241, Indonesia', rating=4.6, total_ratings=100, googleMapsURL='https://maps.google.com/?cid=18085236407562543250&g_mp=Cilnb29nbGUubWFwcy5wbGFjZXMudjEuUGxhY2VzLlNlYXJjaE5lYXJieRAAGAQgAA', websiteURL='https://www.instagram.com/fordocoffee/', regularOpeningHours=['Senin: 08.00–00.00', 'Selasa: 08.00–00.00', 'Rabu: 08.00–00.00', 'Kamis: 08.00–00.00', 'Jumat: 08.00–00.00', 'Sabtu: 08.00–00.00', 'Minggu: 08.00–00.00'], photo=Photo(url='https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=ATKogpe2fWcnmYq0LOprKAcMQezwJ-d7wI6W9XyZD5ySfWc_uXc8fsYUO1TRwjE0NenKfdKKwH45WIC9ykUn4sDG_NeT-RvKw71REm0GeOkjmwWr3mBFdGHg3dL4l5BKnv8-V8Sw32d-L0-ZcBsyewdYBZfN_8Ih4pIfKj0EbYdHhH8IPzpvaXnXEDoFAVR1ZnplB_xH2UHwp9tSMa2SKqaQ8pMYOCADy9HeW0yN_QkIS7Bo_gBClTmRka7nXu_cI6ajNJv23PYa7xIlkfGEEdJTkCtpvhfY8f9KFyPSeYtL1ewWrKw3MP0OZ7jVNUbFgVSdIxm1nTZq2Zh5kQgS3-OPFnH20vWWihW4eaesA8Zfs7lKFzMsSsOf9pg3DyG1Ta6OeKOLOyRX4k7jO5intCwkwUZVfhw3M0yN3rGpAw6SJCT9uCc&key=AIzaSyByX6zAtiVo9qYDr46kswF828RfopoJL68', authorName='Agus Wahyudi', authorURL='https://maps.google.com/maps/contrib/110437766218191946398'), priceRange={'startPrice': {'currencyCode': 'IDR', 'units': '25000'}, 'endPrice': {'currencyCode': 'IDR', 'units': '50000'}}, accessibilityOptions={'wheelchairAccessibleSeating': False}, details=Details(servesBreakfast=None, servesLunch=None, servesDinner=None, servesBrunch=None, outdoorSeating=True, liveMusic=None, servesDessert=True, servesCoffee=True, goodForChildren=None, allowsDogs=False, restroom=True, goodForGroups=False, parkingOptions={'freeParkingLot': True, 'freeStreetParking': True, 'freeGarageParking': False}, paymentMethods={'acceptsCreditCards': True, 'acceptsDebitCards': True, 'acceptsCashOnly': False, 'acceptsNfc': True}), reviews=['Nyesel baru kali ini nyoba kopi berry blast & dirty matcha nyaaaaa dijogja 😭❤️ ternyata seenak itu\n\nHarus beli lagi dan lagi sih', 'cocok buat nyantai sore, buat rasa jangan diragukan coffe beans mereka roasting sendiri, bahkan bisa milih pilihan beans mereka. Recomended bgt buat yang mau cari taste beans coffe yang beneran kopi.\n\nKurang cocok buat nugas dan belajar ya, karena bisa karena suara mesin, kurang akses charger dan agak panas namun sejuk krn open space. Tapi no worries akses wifi mereka kencang 😍', 'Nemenein anak lanang explore perkopian di jogja disela2 kegiatan.\nWaooo rasa kopinya mantep...', 'Dateng siang dan direkomendasiin berry blast..Rasanya kopi berry seger bikin mata melek dari ngantuk dan lambung tetep aman jadi untuk wfh (LT 2) tempat ini lumayan cocok. Padahal lambung saya sensitif banget sama kopi.Minusnya ngga ada makan berat dan musholla aja sih..cuman ada snack..', 'Anda suka nongkrong? Atau anda suka mengopi? Coba dan rasakan minuman serta makanan disini, dengan berbagai menu makanan dan minuman yang bervariasi sesuai dengan keinginan anda, baik dari coffee ataupun non-coffe, tersedia juga makanan sebagai pendamping ngobrol santai anda dengan teman, sahabat, pacar atau bahkan relasi anda.\nTempatnya nyaman, dan tempat ini juga ada alat roasting kopi, bagi yang mau beli kopi, juga tersedia kopi kemasan.\n\nMinuman : 8/10\n\nPenilaian tersebut berdasarkan nilai pribadi, enak dan tidak enak adalah relatif, sehingga setiap orang memiliki penilaian yang berbeda. Silahkan butikan dan coba sendiri. Terima kasih.'], landmarks=['finance', 'store', 'establishment', 'bank', 'point_of_interest', 'car_repair', 'place_of_worship'])]
        
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
