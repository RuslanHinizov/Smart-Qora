# Smart Qora — Çiftlik Sayım ve Bölge Envanteri Planı

## Amaç

Smart Qora, kapıdan geçen hayvanı saymanın yanında hayvan gruplarının çiftlik
içindeki bölge bazlı sayısını tutacak. Kapsam yalnızca şunlardır:

1. Çiftlik bölgeleri (ağıl, mera, karantina, dış alan gibi).
2. Hayvan grupları (koyun, kuzu, koç, dana gibi).
3. Başlangıç envanteri.
4. Kamera kaynaklı bölgeler arası hareketler.
5. Manuel fiziksel sayım ve fark düzeltmesi.

Bireysel hayvan profili, RFID, sağlık, yem, satış ve finans modülleri bu
kapsama dahil değildir.

## Temel kurallar

- Sayım yalnızca bir **grup** için tutulur; sistem tek hayvan kimliği iddia etmez.
- Her kamera kapısı iki bölgeye bağlanır: `dış bölge` ve `iç bölge`.
  `IN`, dış bölgeden iç bölgeye; `OUT`, iç bölgeden dış bölgeye harekettir.
- Hareket geçmişi değiştirilemez. Yanlış sayım, geçmişi silerek değil, neden
  bilgisi olan bir manuel düzeltme hareketiyle düzeltilir.
- Bölge/grup bakiyesi, başlangıç envanteri ve hareketlerden hesaplanır. Aynı
  işlemde hem hareket hem bakiye güncellenir; yarım kayıt oluşamaz.
- Bir kamera olayı en fazla bir stok hareketi doğurur. Tekilleştirme kamera
  olayı üzerinden yapılır.
- Bakiye eksiye düşemez. Böyle bir kamera hareketi kaydedilmez; uygulama ve
  Telegram üzerinden "sayım doğrulaması gerekli" alarmı oluşur.
- Yönetici envanter, bölge, grup, kamera bağlantısı ve düzeltme yapabilir.
  Viewer yalnızca görüntüler.

## Veri modeli

### `farm_zones`

`id`, `name`, `kind`, `is_active`, `sort_order`, `created_at`.

`kind`: `PEN`, `PASTURE`, `QUARANTINE`, `EXTERNAL`.
`EXTERNAL`, çiftlik dışı giriş/çıkışları temsil eder ve silinemez.

### `animal_groups`

`id`, `name`, `species`, `is_active`, `sort_order`, `created_at`.

Örnek: `Koyunlar / sheep`, `İnekler / cattle`, `Keçiler / goat`,
`Atlar / horse`. Kamera, modelin tespit ettiği türü otomatik olarak doğru
gruba yazar: `sheep → koyun`, `cattle → inek`, `goat → keçi`,
`horse → at`. Böylece aynı kapıdan farklı hayvan türleri geçebilir.

`Kuzu` ve `koç` da teknik olarak `sheep` türüdür. Kamera yaş veya cinsiyet
ayırt edemediği için bu ayrım gerektiğinde yönetici kamera ayarında o türün
varsayılan grubunu seçer; aksi halde tek bir `Koyun` grubu kullanılır.

### `inventory_balances`

`zone_id`, `group_id`, `quantity`, `updated_at`.

Her bölge + grup için tek satırdır. Hızlı panel okuması bu tablodan yapılır.

### `inventory_movements`

`id`, `group_id`, `from_zone_id`, `to_zone_id`, `quantity`, `kind`,
`source_event_id`, `note`, `created_by_user_id`, `created_at`.

`kind`: `INITIAL`, `CAMERA`, `MANUAL_ADJUSTMENT`, `TRANSFER`.

Bir kamera olayı varsa `source_event_id` benzersizdir. Böylece worker tekrar
çalışsa bile aynı geçiş ikinci kez stok hareketi yapmaz.

### `inventory_reconciliations`

`id`, `zone_id`, `group_id`, `expected_quantity`, `physical_quantity`,
`difference`, `note`, `created_by_user_id`, `created_at`.

Fiziksel sayım sonrası fark kaydedilir ve bunun karşılığı olan bir
`MANUAL_ADJUSTMENT` hareketi oluşturulur.

### Kamera bağlantısı

Kameraya yalnızca `inside_zone_id` ve `outside_zone_id` eklenir. Kamera
geçen hayvanın türünü model sonucundan alır ve eşleşen aktif gruba otomatik
yazar. Kamera aktif değilse veya iki bölge tamamlanmamışsa görüntü yayınlanır
ama stok hareketi yapılmaz; panelde "envanter bağlantısı eksik" gösterilir.

## İş akışları

### İlk kurulum

1. Yönetici bölgeleri ve grupları oluşturur.
2. Her bölge/grup için fiziksel başlangıç sayısı girer.
3. Sistem `INITIAL` hareketleri ve bakiyeleri oluşturur.
4. Kamera, iç ve dış bölgeyle bağlanır. Koyun, inek, at ve keçi gibi farklı
   türler aynı kameradan kendi gruplarına otomatik yazılır.

### Kamera geçişi

1. Görüntü worker'ı `IN` veya `OUT` olayı üretir.
2. Olayın daha önce hareket üretip üretmediği kontrol edilir.
3. `IN`: dış bölge azalır, iç bölge artar. `OUT`: tersi uygulanır.
4. Olay, hareket ve iki bakiye tek veritabanı işleminde kaydedilir.
5. Panel ve Telegram yeni bölge stoklarını canlı alır.

### Manuel sayım doğrulaması

1. Personel bölge ve grubu seçip fiziksel sayıyı girer.
2. Sistem beklenen sayı ile farkı gösterir.
3. Onaylandığında fark kadar `MANUAL_ADJUSTMENT` hareketi eklenir.
4. Neden alanı zorunludur: `kamera farkı`, `doğum`, `ölüm`, `satış`, `diğer`.
5. Düzeltme geçmişi silinmez ve raporda ayrı gösterilir.

## API

- `GET/POST/PUT /api/farm/zones`
- `GET/POST/PUT /api/farm/groups`
- `GET /api/inventory/summary`
- `GET /api/inventory/movements`
- `POST /api/inventory/initialise`
- `POST /api/inventory/transfer`
- `POST /api/inventory/reconcile`
- Kamera `GET/PUT` yanıtına iç/dış bölge bağlantısı eklenir.

## Arayüz

- Yeni **Çiftlik** sayfası: bölgeler, gruplar ve başlangıç envanteri.
- Ana panel: toplam yerine bölgelere göre canlı tablo; örneğin
  `Mera 110 koyun`, `Ağıl A 58 koyun`.
- Kamera düzenleme ekranı: iç bölge ve dış bölge seçimi; türden gruba
  otomatik eşleştirme durumu.
- Yeni **Envanter** sayfası: hareket geçmişi, filtreler, manuel aktarım ve
  fiziksel sayım doğrulama formu.
- Olay geçmişi, kamera olayını bağlı envanter hareketiyle gösterir.

## Uygulama sırası

1. Alembic migrasyonu, SQLAlchemy modelleri ve başlangıç verileri.
2. Atomik envanter servisi, API'ler ve yetki kontrolleri.
3. Kamera olayının envanter hareketine bağlanması.
4. Çiftlik, envanter ve kamera yapılandırma arayüzleri.
5. Canlı WebSocket güncellemeleri ve Telegram mesajları.
6. Birim, entegrasyon, migration ve Docker testleri.
7. Temiz demo verisiyle giriş/çıkış/doğrulama uçtan uca kontrolü.

## Kabul kriterleri

- Aynı kamera olayı ikinci kez stok değiştiremez.
- Bir geçişte kaynak bölge ve hedef bölge toplamı korunur.
- Manuel düzeltme, nedeni ve yapan kullanıcı olmadan kaydedilemez.
- Kamera bağlantısı eksikken otomatik stok değişmez.
- Viewer hiçbir envanter verisini değiştiremez.
- Yeniden başlatma ve video döngüsü stokları şişirmez.
