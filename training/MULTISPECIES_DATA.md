# Smart Qora — çok tür eğitim verisi

Hedef model yalnızca dört üretim sınıfı öğrenir: `sheep`, `cattle`, `goat`,
`horse`. İnsan, köpek ve araç bu sınıflara **asla** etiketlenmez. Böylece
model onları hayvan olarak saymaz; mevcut köpek koruması ikinci bir güvenlik
katmanı olarak kalır.

## Seçilen kaynaklar

| kaynak | türler | neden seçildi | lisans / kullanım |
|---|---|---|---|
| Yerel geçit kayıtları | gerçek sahadaki türler | kamera açısı, çizgi, sık sürü ve ışık koşulu tam olarak kurulumla aynıdır | müşteri izniyle; eğitimden önce elle düzeltilmiş etiket gerekir |
| [AUTH-Sheep](https://zenodo.org/records/13843376) | koyun, keçi, at | 4 üstten çekimli video, kare-kare kutular ve sabit takip kimlikleri; sayım işi için en yakın açık video kaynağı | CC BY 4.0; atıf zorunlu |
| [CattleEyeView](https://github.com/AnimalEyeQ/CattleEyeView) | sığır | 14 üstten çekimli video / 30.703 kare; sayım ve takip için hazırlanmış | depo Apache-2.0; veri indirme şartları indirirken ayrıca kayıt altına alınır |
| [Open Images V7](https://storage.googleapis.com/openimages/web/download_v7.html) seçilmiş altkümesi | koyun, sığır, keçi, at, köpek | dört türü farklı ırk, ışık ve arka planlarda dengeler; köpek negatif örneği sağlar | her görüntünün kaynak lisansı kayıt altına alınır; otomatik seçimden sonra lisans denetimi yapılır |

`AUTH-Sheep` indirmek için:

```powershell
python training/download_auth_sheep.py
```

İndirme kesilirse aynı komut devam eder ve MD5 doğrulaması yapar. Veri
`datasets/_downloads/` altında kalır, Git'e girmez.

## Eğitim sırası

1. Yerel 24 videodan farklı saat/ışık/kapı yönlerini kapsayan kareler seçilir.
2. Her karedeki koyun, sığır, keçi ve at kutusu CVAT'ta gözden geçirilir.
3. Dış kaynaklar sınıf dengesi ve farklı görünüş için eklenir; video bazlı
   train/validation/test ayrımı korunur. Aynı videonun komşu kareleri farklı
   bölümlere asla bölünmez.
4. Tek YOLO modeli eğitilir; sonra gerçek geçit videosunda üretimdeki aynı
   takipçi ve sayım çizgisi ile giriş/çıkış testi yapılır.
5. Yeni model ancak hem tür bazlı tespit hem de sayım testi eski modelden iyi
   ise `models/best.pt` olarak devreye alınır. Değilse eski model korunur.

Bu süreçte amaç çok sayıda video eklemek değil; her tür ve sahne için doğru
etiketli, dengeli veri ile gerçek kapıdaki sayım hatasını azaltmaktır.
