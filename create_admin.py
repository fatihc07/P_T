import requests
import json

# Bilgiler
url_list = "https://grxnilesgytsxkpzotjw.supabase.co/auth/v1/admin/users"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyeG5pbGVzZ3l0c3hrcHpvdGp3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQyOTk0OCwiZXhwIjoyMDkwMDA1OTQ4fQ.rGa8VFsVrbEhuDYy1gRRwGVHqxgO02aqJI2VhDuf5o4"

headers = {
    "Authorization": f"Bearer {key}",
    "apikey": key,
    "Content-Type": "application/json"
}

print(f"📡 Admin kullanicisi araniyor...")
try:
    r = requests.get(url_list, headers=headers)
    response_data = r.json()
    
    # Supabase'de kullanicilar 'users' anahtari altindadir
    users_list = response_data.get('users', [])
    admin_user = next((u for u in users_list if u['email'] == 'admin@admin.com'), None)
    
    if admin_user:
        user_id = admin_user['id']
        url_update = f"{url_list}/{user_id}"
        
        # Sifreyi guncelle ve e-postayi onaylanmis yap
        update_data = {
            "password": "admin_1234",
            "email_confirm": True
        }
        r_update = requests.put(url_update, headers=headers, json=update_data)
        
        if r_update.status_code == 200:
            print("✅ ADMIN SİFRESİ BAŞARIYLA admin_1234 OLARAK GÜNCELLENDİ!")
        else:
            print(f"❌ Güncelleme Hatası ({r_update.status_code}): {r_update.text}")
    else:
        print("❌ Admin kullanıcısı bulunamadı!")

except Exception as e:
    print(f"❌ Bağlantı Hatası: {e}")
