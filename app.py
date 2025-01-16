from flask import Flask, render_template, request, jsonify
import json
import joblib
import os

app = Flask(__name__)

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"JSON dosyası yükleme hatası: {str(e)}")
        return None

# Önce global değişkenleri tanımlayalım
model = None
job_encoder = None

def load_model_files():
    global model, job_encoder
    
    try:
        # Model dosyası yolu
        model_path = 'burs_model.pkl'
        encoder_path = 'job_encoder.pkl'  # .json yerine .pkl kullanıyoruz
        
        print(f"Model dosyası yolu: {model_path}")
        print(f"Encoder dosyası yolu: {encoder_path}")
        
        # Dosyaların varlığını kontrol et
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model dosyası bulunamadı: {model_path}")
        if not os.path.exists(encoder_path):
            raise FileNotFoundError(f"Encoder dosyası bulunamadı: {encoder_path}")
        
        # Dosyaları joblib ile yükle
        model = joblib.load(model_path)
        job_encoder = joblib.load(encoder_path)  # 
        
        print("Model ve encoder başarıyla yüklendi")
        print("Encoder örnek içerik:", list(job_encoder.keys())[:5])  # Kontrol için ilk 5 mesleği yazdır
        
        return True
        
    except Exception as e:
        print(f"Model yükleme hatası: {str(e)}")
        return False

# Uygulama başlangıcında dosyaları yükle
if not load_model_files():
    print("UYARI: Model ve encoder yüklenemedi!")



# Gelir aralıkları tanımlaması
INCOME_RANGES = {
    '2020': [
        {'range': '2.324 TL - 5.000 TL', 'avg': 3662},
        {'range': '5.000 TL - 7.972 TL', 'avg': 6486},
        {'range': '7.973 TL - 9.296 TL', 'avg': 8634.5},
        {'range': '9.297 TL - 11.620 TL', 'avg': 10458.5},
        {'range': '11.621 TL ve üzeri', 'value': 11621}
    ],
    '2021': [
        {'range': '2.825 TL - 5.650 TL', 'avg': 4237.5},
        {'range': '5.651 TL - 8.475 TL', 'avg': 7063},
        {'range': '8.476 TL - 11.300 TL', 'avg': 9888},
        {'range': '11.301 TL - 15.125 TL', 'avg': 13213},
        {'range': '15.125 TL ve üzeri', 'value': 15125}
    ],
    '2022': [
        {'range': '4.253 TL - 8.506 TL', 'avg': 6379.5},
        {'range': '8.507 TL - 12.759 TL', 'avg': 10633},
        {'range': '12.760 TL - 17.012 TL', 'avg': 14886},
        {'range': '17.013 TL - 21.265 TL', 'avg': 19139},
        {'range': '21.266 TL ve üzeri', 'value': 21266}
    ],
    '2023': [
        {'range': '8.500 TL - 13.000 TL', 'avg': 10750},
        {'range': '13.000 TL - 17.500 TL', 'avg': 15250},
        {'range': '17.500 TL - 22.000 TL', 'avg': 19750},
        {'range': '22.000 TL - 28.500 TL', 'avg': 25250},
        {'range': '28.501 TL ve üzeri', 'value': 28501}
    ],
    '2024': [
        {'range': '10.506 TL - 17.500 TL', 'avg': 14003},
        {'range': '17.501 TL - 25.518 TL', 'avg': 21509.5},
        {'range': '25.519 TL - 33.024 TL', 'avg': 29271.5},
        {'range': '33.025 TL - 41.530 TL', 'avg': 37277.5},
        {'range': '41.531 TL ve üzeri', 'value': 41531}
    ]
}

# Şehir ve meslek verilerini yükle
cities_data = load_json_file('cities.json')
occupations_data = load_json_file('occupations.json')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_cities')
def get_cities():
    return jsonify(cities_data)

@app.route('/get_occupations')
def get_occupations():
    return jsonify(occupations_data)

@app.route('/get_income_ranges/<year>')
def get_income_ranges(year):
    """Seçilen yıla göre gelir aralıklarını döndür"""
    if year in INCOME_RANGES:
        ranges = [range_info['range'] for range_info in INCOME_RANGES[year]]
        return jsonify({'ranges': ranges})
    return jsonify({'ranges': []})

def calculate_income_value(year, selected_range):
    """Seçilen gelir aralığına göre ortalama veya sabit değeri hesapla"""
    if year not in INCOME_RANGES:
        return None
    
    for range_info in INCOME_RANGES[year]:
        if range_info['range'] == selected_range:
            # Eğer "ve üzeri" varsa sabit değeri, yoksa ortalamayı döndür
            return range_info.get('value', range_info.get('avg'))
    
    return None


def check_direct_qualification(data):
    """
    Özel durumları kontrol et.
    Return: (bool, probability, type) - qualification result, probability, and type ('Burs' or 'Kredi').
    """
    # Şehir kontrolü
    city_of_study = data.get('city_of_study', '').lower()
    city_of_residence = data.get('city_of_residence', '').lower()
    if city_of_study == city_of_residence:
        return True, 90, 'Kredi'

    # Öğretim durumu kontrolü
    teaching_status = data.get('teaching_status', '')
    if teaching_status in ['acik', 'uzaktan']:
        return True, 90, 'Kredi'

    return False, None, None

def encode_jobs(job, job_map):
    """Meslek encoding işlemi"""
    if not job or job == '0':
        return 0
    return job_map.get(job.lower(), 0)

def calculate_priority_score(data):
    """Burs öncelik puanını hesapla"""
    score = 0
    
    if data.get('special_status', '') != 'yok':
        score += 2
    
    family_status = data.get('family_status', '')
    if family_status != 'birlikte':
        score += 1
    
    return score

def prepare_data_for_model(form_data):
    """Form verilerini model için hazırla"""
    features = {}
    
    # Temel sayısal veriler
    features['Aylık Ev Geliri'] = calculate_income_value(form_data.get('application_year'), 
                                                       form_data.get('monthly_income_range'))
    
    siblings_count = float(form_data.get('siblings_count', 0))  # Ailedeki toplam kişi sayısı (anne, baba, çocuklar)
    siblings_number = float(form_data.get('siblings_number', 0))  # Kardeş sayısı (sadece diğer çocuklar)

    features['Toplam Aile Üyesi Sayısı'] = siblings_count
    features['Kaç kardeşiniz var? (Yoksa 0 girin.)'] = siblings_number  # Yalnızca kardeş sayısı
    features['Eviniz Var mı? kaç tane'] = float(form_data.get('house_count', 0))
    features['Arabanız Var mı? kaç tane'] = float(form_data.get('car_count', 0))
    
    
     # Anne/Baba mesleği işleme
    family_status = form_data.get('family_status', '')

# Eğer ailevi durum "Anne veya baba vefat etmiş" ise, meslek bilgileri sıfırlanır
    if family_status == 'vefat':  # HTML'deki "vefat" value değerini karşılaştırıyoruz
      features['Anne Mesleği'] = 0
      features['Baba Mesleği'] = 0

# Eğer sadece anne ile birlikte yaşanıyorsa (HTML'deki "anne" değeri)
    elif family_status == 'anne':  # HTML'deki "anne" value değeri ile karşılaştırma
      features['Anne Mesleği'] = encode_jobs(form_data.get('mother_job'), job_encoder)
      features['Baba Mesleği'] = 0

# Eğer sadece baba ile birlikte yaşanıyorsa (HTML'deki "baba" değeri)
    elif family_status == 'baba':  # HTML'deki "baba" value değeri ile karşılaştırma
      features['Anne Mesleği'] = 0
      features['Baba Mesleği'] = encode_jobs(form_data.get('father_job'), job_encoder)

# Diğer durumlar (Anne ve baba birlikte, Anne ve baba ayrı)
    else:
      features['Anne Mesleği'] = encode_jobs(form_data.get('mother_job'), job_encoder)
      features['Baba Mesleği'] = encode_jobs(form_data.get('father_job'), job_encoder)
    


    # Diğer özellikler
    features['Başvuru Yılı'] = float(form_data.get('application_year', 0))
    features['Burs_Oncelik_Puani'] = calculate_priority_score(form_data)
    features['Ailevi_Durum_Oncelik'] = 0 if family_status == 'birlikte' else 1
    features['Kira Durumunuz'] = 0 if form_data.get('rent_status') == 'evet' else 1
    features['Burs alan kardeşiniz oldu mu ?'] = 1 if form_data.get('has_scholarship_brother') == 'evet' else 0
    

    # Model için feature listesini oluştur
    feature_list = [
        features['Aylık Ev Geliri'], features['Baba Mesleği'], features['Anne Mesleği'],
        features['Başvuru Yılı'], features['Toplam Aile Üyesi Sayısı'],
        features['Kaç kardeşiniz var? (Yoksa 0 girin.)'], features['Eviniz Var mı? kaç tane'],
        features['Arabanız Var mı? kaç tane'], features['Burs_Oncelik_Puani'],
        features['Ailevi_Durum_Oncelik'], features['Kira Durumunuz'],
        features['Burs alan kardeşiniz oldu mu ?']
    ]
    
    return feature_list

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Model ve encoder kontrolü
        if model is None or job_encoder is None:
            return jsonify({
                'error': 'Model veya encoder yüklenemedi. Lütfen sistem yöneticisiyle iletişime geçin.'
            }), 500
            
        form_data = request.form.to_dict()
        print("Alınan form verileri:", form_data)

        # Zorunlu alanları kontrol et
        required_fields = ['monthly_income', 'application_year', 'siblings_count']
        for field in required_fields:
            if field not in form_data or not form_data[field]:
                raise ValueError(f"Eksik alan: {field}")
        
        # Özel durum kontrolü
        is_qualified, direct_probability, qual_type = check_direct_qualification(form_data)
        print("Özel durum kontrolü sonuçları:", is_qualified, direct_probability, qual_type)
        
        if is_qualified:
            return jsonify({
                'prediction': f'{qual_type} Alma İhtimali',
                'probability': direct_probability,
                'reason': 'Özel durum nedeniyle doğrudan değerlendirme'
            })

        # Veri hazırlama - sizin mevcut fonksiyonunuzu kullan
        features = prepare_data_for_model(form_data)
        print("Hazırlanan özellikler:", features)
        
        # Feature sayısını kontrol et
        expected_features = 12  # Modelinizde kullandığınız feature sayısı
        if len(features) != expected_features:
            raise ValueError(f"Hazırlanan özellik sayısı ({len(features)}) beklenen sayıdan ({expected_features}) farklı")
            
        # Tahmin
        probability = model.predict_proba([features])[0][0] * 100  # [0][0] burs olasılığını verir
        prediction = 'Burs Alma İhtimali' if probability > 50 else 'Kredi Alma İhtimali'
        
        return jsonify({
            'prediction': prediction,
            'probability': round(probability, 2)
        })

    except ValueError as ve:
        print(f"Doğrulama hatası: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
        
    except Exception as e:
        print(f"Tahmin hatası: {str(e)}")
        print("Hata detayı:", traceback.format_exc())  # Detaylı hata mesajı
        return jsonify({'error': 'Tahmin sırasında bir hata oluştu'}), 500

if __name__ == '__main__':
    app.run(debug=True)