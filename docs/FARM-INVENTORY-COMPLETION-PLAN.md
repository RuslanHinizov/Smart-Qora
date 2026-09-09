# Smart Qora — Çiftlik Envanteri: Bitirme ve Düzeltme Planı

Bu doküman `docs/FARM-INVENTORY-PLAN.md`'nin devamıdır. O plan **ne yapılacağını**
anlatıyordu; bu plan, commit'lenmemiş mevcut uygulamanın **nerede eksik/hatalı
kaldığını** ve onu bitirmek için ne yapılması gerektiğini anlatır.

Durum tespiti: orijinal planın 7 adımından 1–4 uygulanmış (migrasyon, model,
servis, API, kamera bağlantısı, Çiftlik sayfası), 5–7 (canlı bildirimler,
testler, uçtan uca doğrulama) eksik. Ek olarak, uygulanan kısımda envanteri
**pratikte çalışmaz hale getiren** bir mantık hatası var (Faz 1, madde 1.1).

Toplam commit'lenmemiş iş: 21 dosya, ~978 satır ekleme.

> **Durum (bu oturumda):** Faz 0 ve Faz 1 tamamlandı ve commit'lendi
> (`ac26f24`, `1221cd7`). Faz 2'den itibaren henüz başlanmadı.

---

## Faz 0 — Yeşil taban ✅ tamamlandı (`ac26f24`)

Hiçbir şeye dokunmadan önce test paketi yeşil olmalı; aksi halde sonraki
değişikliklerin neyi bozduğu anlaşılmaz.

### 0.1 · Test ortamı yerel `.env`'den sızıyor

**Sorun.** `tests/test_counting_integration.py::test_video_loop_replays_without_inflating_counts`
yerelde başarısız (`assert 0 == 1`), CI'da geçiyor.

**Neden.** `backend/.env` (git-ignored) içinde `VIDEO_LOOP_RESET=true` var.
`conftest.py` bu değeri nötrleştirmiyor, test de sadece `video_loop`'u
monkeypatch ediyor. Sonuç: `_reset_demo_loop()` çalışıp olayları siliyor.
CI'da `backend/.env` olmadığı için varsayılan `False` kalıyor ve test geçiyor.

**Çözüm.** `tests/conftest.py`'deki ortam bloğuna ekle:

```python
os.environ["VIDEO_LOOP_RESET"] = "false"
```

Aynı blokta `VIDEO_LOOP`, `NON_LIVESTOCK_GUARD`, `TRACKER`, `DEVICE` gibi
worker davranışını değiştiren diğer anahtarlar için de açık varsayılan ver —
prensip: **test ortamı ambient `.env`'den bağımsız olmalı.**

**Doğrulama.** `cd backend && pytest -q` → 122 passed, ve
`VIDEO_LOOP_RESET=true pytest -q` de 122 passed.

---

## Faz 1 — Envanteri gerçekten çalışır hale getir ✅ tamamlandı (`1221cd7`)

Bu fazdaki maddeler kozmetik değil: 1.1 olmadan kamera envanteri **hiç**
güncellemez.

### 1.1 · İlk `IN` geçişi her zaman reddediliyor *(kritik)* ✅

**Sorun.** Tipik kurulumda kamera envanteri asla artırmaz.

**Neden.** `inventory_service.apply_movement` her `from_zone_id` için
"kaynak bölgede yeterli hayvan yok" kontrolü yapıyor. Kamera `IN` olayında
kaynak bölge = `outside_zone_id` (mera / dış alan). Yönetici doğal olarak
sadece ağılın başlangıç sayısını girer; mera bakiyesi 0'dır. Dolayısıyla:

```
apply_movement(from=Mera(0), to=Ağıl)  →  409 "Insufficient animals…"
```

`counting_service._save_event` bu `HTTPException`'ı yakalayıp sadece log
yazıyor (`inventory_camera_movement_skipped`), olayı yine de commit ediyor.
Sonuç: **sayım artar, envanter artmaz, kimse haberdar olmaz.**

**Çözüm.** `EXTERNAL` türündeki bölgeleri sınırsız kaynak/hedef kabul et.
Plan zaten `EXTERNAL`'ı "çiftlik dışı giriş/çıkış" olarak tanımlıyor — çiftlik
dışındaki hayvan sayısı bilinmiyor, dolayısıyla negatife düşme kuralı oraya
uygulanamaz.

`apply_movement` içinde kaynak kontrolünü bölge türüne bağla:

```python
source_zone = await session.get(FarmZone, from_zone_id)
if source_zone.kind is not ZoneKind.EXTERNAL and source.quantity < quantity:
    raise HTTPException(409, "…")
```

`EXTERNAL` bakiyesinin negatife düşmesine izin ver (o sayı "dışarıya net akış"
anlamına gelir ve bilgi taşır). `inventory_balances` tablosunda `quantity`
üzerinde CHECK yok, migrasyon değişikliği gerekmez.

**Ek karar (dokümante edilmeli).** `PASTURE` bölgesi *çiftlik içi* sayıldığı
için negatife düşemez. Kameranın dış bölgesi bir meraysa ve mera boşsa `IN`
yine bloklanır — bu doğru davranıştır ve 1.4'teki alarmla görünür olur.
Kurulum sihirbazı (2.4) yöneticiyi dış bölge olarak `EXTERNAL` seçmeye
yönlendirmeli.

**Doğrulama.** Yeni test: ağıl=100, dış=`EXTERNAL`(0) kurulumunda bir `IN`
olayı üret → ağıl 101, `EXTERNAL` −1, bir adet `CAMERA` hareketi.

### 1.2 · `inside_zone_id == outside_zone_id` engellenmiyor ✅

**Sorun.** Yönetici kamera formunda aynı bölgeyi hem iç hem dış seçebilir.
Her geçişte `apply_movement` 422 fırlatır, yutulur, envanter hiç güncellenmez.

**Çözüm.** `schemas.CameraCreate.valid_geometry` içine (veya ayrı bir
validator'a):

```python
if self.inside_zone_id is not None and self.inside_zone_id == self.outside_zone_id:
    raise ValueError("Inside and outside zones must differ")
```

**Doğrulama.** `PUT /api/cameras/1` aynı iki bölgeyle → 422.

### 1.3 · Var olmayan bölge id'si yanlış hata veriyor ✅

**Sorun.** `inside_zone_id: 999` gönderilirse FK ihlali olur;
`cameras.commit_camera` bunu `IntegrityError` sanıp
`409 "Camera configuration changed concurrently; reload and retry"` döner.
Yönetici için tamamen yanıltıcı.

**Çözüm.** `create_camera` / `update_camera` içinde commit'ten önce bölge
varlığını doğrula, yoksa `404 "Farm zone not found"`. `inventory.py`'deki
`_require_zone_and_group` yardımcısı buraya taşınabilir (ör.
`app/services/inventory_service.py` ya da küçük bir `farm_lookup` yardımcısı).

**Doğrulama.** Olmayan bölge id'si ile `PUT` → 404, mesaj net.

### 1.4 · Envanter hareketi düşünce kimse haberdar olmuyor *(plandaki kabul kriteri)* ✅

**Sorun.** Orijinal plan diyor ki:
> "Bakiye eksiye düşemez. Böyle bir kamera hareketi kaydedilmez; uygulama ve
> Telegram üzerinden **'sayım doğrulaması gerekli'** alarmı oluşur."

Şu an sadece `logger.warning` var.

**Çözüm.** İki kopuk-envanter durumu için tek bir alarm yolu kur:

| durum | log anahtarı | anlamı |
|---|---|---|
| kaynak bölge yetersiz | `inventory_camera_movement_skipped` | fiziksel sayım gerekli |
| tür için grup bulunamadı | `inventory_group_not_configured` | kurulum eksik |

`app/telegram/notifications.py`'ye `ALERT` sözlüğüne 4 dilde iki anahtar ekle
(`inventory_mismatch`, `inventory_unconfigured`), `counting_service` içinden
`notifier.alert(...)` çağır.

**Spam koruması şart** — sürü geçerken saniyede onlarca olay olur. Mevcut
`NotificationAggregator` yön bazlı çalıştığı için burada uygun değil; en basit
çözüm `CountingService` üzerinde bir "son alarm zamanı" alanı ve sabit bir
soğuma (ör. 15 dk) tutmak. Aynı bilgiyi panelde de göster: `/api/status`
yanıtına `inventory_health: "ok" | "mismatch" | "unconfigured"` alanı ekle,
Dashboard'da uyarı şeridi olarak render et.

**Doğrulama.** Yetersiz kaynakla 50 geçiş üret → tam 1 Telegram mesajı,
`/api/status` → `inventory_health: "mismatch"`.

### 1.5 · Başarısız harekette sahte sıfır bakiye satırı kalıyor ✅

**Sorun.** `_locked_balance` bakiye satırı yoksa `quantity=0` ile oluşturup
`flush` ediyor; yetersizlik kontrolü **ondan sonra** fırlatıyor. API yolunda
zararsız (`get_session` commit etmeden kapanır), ama **worker yolunda**
`_save_event` istisnayı yutup `session.commit()` yaptığı için o sıfır satır
kalıcı olur ve `/inventory/summary`'de anlamsız bir `0` satırı görünür.

**Çözüm.** `_locked_balance`'a `create: bool = True` parametresi ekle;
kaynak bakiye okunurken `create=False` ile çağır ve `None` dönerse
`quantity=0` kabul edip kontrolü yap. Satır sadece gerçekten yazılacaksa
oluşturulsun.

**Doğrulama.** Yetersiz kaynakla bir kamera olayı → `inventory_balances`'ta
yeni satır yok.

---

## Faz 2 — Plandaki eksik işlevler

### 2.1 · `POST /api/inventory/transfer` arayüzde yok

Backend uç noktası, şeması ve testi var; frontend'de **hiç** kullanılmıyor.
`useFarmMutations` yalnızca `createZone / createGroup / initialise / reconcile`
sağlıyor. Plan "manuel aktarım formu" istiyordu.

**Çözüm.** `queries.ts`'e `transfer` mutation'ı, Çiftlik sayfasına
"Bölgeler arası aktarım" kartı: grup / kaynak bölge / hedef bölge / adet /
zorunlu not. `note` backend'de `min_length=3` — form bunu doğrulamalı.

Aynı yerde eksik olan diğer mutation'lar: `PUT /farm/zones/{id}` ve
`PUT /farm/groups/{id}` de arayüzde yok (bölge/grup adı düzeltilemiyor,
pasife alınamıyor). `updateZone` / `updateGroup` ekle.

### 2.2 · Tür → grup çakışması sessizce envanteri durduruyor

**Sorun.** `group_for_detection`, aynı türde **tam olarak bir** aktif grup
varsa onu döndürüyor; 2+ varsa `None`. Yani yönetici "Koyun" ve "Kuzu"
gruplarını (ikisi de `species=sheep`) oluşturduğu anda kamera envanter
yazmayı bırakır — plandaki senaryo tam olarak budur:

> "Kuzu ve koç da teknik olarak sheep türüdür… bu ayrım gerektiğinde
> **yönetici kamera ayarında o türün varsayılan grubunu seçer**."

O alan hiç eklenmemiş.

**Çözüm (iki seçenek, biri seçilmeli):**

- **A — kamera bazlı eşleme tablosu.** Yeni migrasyon `0011`:
  `camera_species_groups(camera_id, species, group_id)`. Kamera düzenleme
  ekranında her tür için grup seçici. Plana en sadık, ama en fazla iş.
- **B — grup üzerinde `is_default` bayrağı.** `animal_groups`'a
  `is_default_for_species boolean` ekle; tür başına en fazla bir tane
  (kısmi unique index). `group_for_detection` önce varsayılanı arar.
  Belirgin biçimde daha az iş, tek kameralı kutu modeline yeterli.

**Öneri: B.** Bu kutu aynı anda tek kamera işletiyor; kamera bazlı eşleme
şu an kullanılmayacak bir esneklik olur. B seçilirse plan dokümanına gerekçe
yazılmalı.

Her iki durumda da 1.4'teki `inventory_unconfigured` alarmı devreye girmeli.

### 2.3 · Telegram envanteri hiç bilmiyor

`/status`, `/today`, günlük özet — hepsi yalnızca kapı sayacını gösteriyor.
Yönetici Telegram'dan "hangi bölgede kaç hayvan var" göremiyor.

**Çözüm.** `app/telegram/commands.py`'ye `/envanter` (eş adlar: `/inventory`,
`/qora`) komutu: bölge bazlı satırlar. `T` sözlüğüne 4 dilde metin. Günlük
özete (`DIGEST`) bölge dökümü ekle. `commands.py` ve `notifications.py`
zaten 4 dilli sözlük düzenine sahip; aynı deseni izle.

### 2.4 · Temiz kurulumda çiftlik boş başlıyor

`db/seed.py` yalnızca admin ve varsayılan kamerayı oluşturuyor. Orijinal
planın 1. adımı "migrasyon, modeller ve **başlangıç verileri**" diyordu.
Yeni bir kutuda Dashboard tamamen sıfır gösterir ve kamera envanter yazamaz.

**Çözüm.** `ensure_default_farm(session)` ekle — yalnızca `farm_zones` boşsa:

- `Dışarısı` / `EXTERNAL` (silinemez, kameranın varsayılan dış bölgesi)
- `Ana Ağıl` / `PEN`
- `Mera` / `PASTURE`
- Dört grup: Koyun/sheep, İnek/cattle, Keçi/goat, At/horse

Varsayılan kamerayı `outside_zone_id=Dışarısı`, `inside_zone_id=Ana Ağıl` ile
bağla. Başlangıç adetleri **girilmez** (0) — onu yönetici Çiftlik sayfasından
girer. Bu, Farm.tsx'teki "hızlı kurulum" butonlarının işini de sadeleştirir.

---

## Faz 3 — i18n'i tek çatı altına al

Bu, koddaki en görünür tutarsızlık. Proje `i18n/translations.ts` +
`translations.test.ts` (diller arası anahtar eşitliği testi) üzerine kurulu,
ama yeni iş üç ayrı yerde kendi çeviri mekanizmasını kurmuş:

| yer | ne yapıyor | risk |
|---|---|---|
| `pages/Farm.tsx` | kendi 4 dilli `copy` objesi (~180 satır) | test kapsamı dışı |
| `pages/Dashboard.tsx` | kendi 4 dilli `names` objesi | test kapsamı dışı |
| `components/AppLayout.tsx` | ayrı `FARM_LABEL: Record<Language, string>` + `key: "settings"` hack'i | nav anahtarı yalan söylüyor |
| `pages/Cameras.tsx` | **hiç çeviri yok** — `"Outside zone"`, `"Inside zone"`, `"Not connected"` sabit İngilizce | RU/KK/TR kullanıcıda bozuk |

`grep -c "farm\|zone\|inventory" translations.ts` → **0**.

**Çözüm.**

1. `translations.ts`'e `// farm & inventory` bölümü aç; `en` sözlüğüne tüm
   anahtarları ekle (dosyadaki not: *"English is the source of truth"* —
   `TranslationKey` ondan türetiliyor, eksik anahtar derleme hatası verir).
2. Farm.tsx / Dashboard.tsx yerel sözlüklerini oradan besle, sil.
3. Cameras.tsx'teki üç sabit metni çevir.
4. `AppLayout` NAV tipine gerçek `farm` anahtarı ekle, `label?: "farm"` +
   `FARM_LABEL` hack'ini ve `key: "settings"` yalanını kaldır.

**Doğrulama.** `npm run test` (translations testi artık yeni anahtarları da
kapsar), `npm run typecheck`, ve dört dilde Çiftlik + Kameralar sayfasının
gözle kontrolü.

---

## Faz 4 — Test kapsamı

Şu an yeni özelliğin testi: `test_inventory.py`'de 2 test (kurulum/aktarım/
mutabakat ve aşırı çekim + viewer yetkisi) ve `test_non_livestock_guard.py`'de
3 saf IoU testi. **Kamera → envanter yolunun tek bir testi yok** — ki Faz 1'in
tamamı tam olarak orada.

Eklenecekler:

**`tests/test_farm_routes.py`** *(yeni)*
- zone/group CRUD, `PUT` ile güncelleme
- aynı isimle ikinci kayıt → 409
- viewer için tüm yazma uçları → 403
- `species` pattern dışı değer → 422

**`tests/test_inventory_camera.py`** *(yeni — en önemlisi)*
- `IN` olayı → `CAMERA` hareketi + iki bakiye, `EXTERNAL` negatife düşer *(1.1)*
- aynı `source_event_id` ile ikinci deneme → yeni hareket yok *(plan kabul kriteri)*
- geçişte kaynak + hedef toplamı korunur *(plan kabul kriteri)*
- kamera bölgeleri bağlı değilken stok değişmez *(plan kabul kriteri)*
- `PASTURE` kaynağı yetersizken hareket yok + alarm tetiklenir *(1.4)*
- başarısız harekette sahte bakiye satırı oluşmaz *(1.5)*
- video döngüsü stokları şişirmez *(plan kabul kriteri — `_reset_demo_loop`)*

**`tests/test_cameras.py`'ye ekleme**
- `inside_zone_id == outside_zone_id` → 422 *(1.2)*
- olmayan bölge id'si → 404, 409 değil *(1.3)*

**Frontend**
- `pages.smoke.test.tsx`'e Farm sayfası eklenmeli (şu an kapsam dışı)
- transfer formu için bir etkileşim testi

**Doğrulama.** Plandaki 6 kabul kriterinin her biri için **adı o kriteri
söyleyen** bir test bulunmalı.

---

## Faz 5 — Vision hattı: performans ve kapsam

### 5.1 · `NonLivestockGuard` sıcak yolda ikinci tam inference yapıyor

`verifier.py` mantık olarak temiz (düşük güvenli kutuları COCO modeliyle
çapraz kontrol, IoU ≥ 0.35 ise köpek diye blokla). Ama `observe()`, güveni
0.75 altında **tek bir aday** varsa bile `imgsz=1280` ile tam bir YOLO geçişi
daha çalıştırıyor. Yoğun sürüde bu neredeyse her karede tetiklenir ve GPU
işini pratikte ikiye katlar.

**Çözüm (ölçmeden değiştirme).** Önce RTX 4060'ta gerçek bir klip üzerinde
guard açık/kapalı FPS ölç. Maliyet anlamlıysa:
- kendi kadansı (ör. `NON_LIVESTOCK_EVERY_N_FRAMES=5`) — bir takip kimliği
  bir kez köpek diye işaretlendiğinde zaten kalıcı olarak bloklanıyor,
  her karede bakmaya gerek yok;
- ve/veya guard için daha küçük `imgsz` (640).

**Doğrulama.** Önce/sonra FPS sayısı ve `scripts/count_video.py` ile aynı
klipte aynı sayım sonucu.

### 5.2 · `_reset_demo_loop` kapsamı gereğinden geniş

`VIDEO_LOOP_RESET=true` iken **tüm** `daily_statistics` tablosunu siliyor —
sadece o kameranın günü değil. Demo için yazılmış ve öyle belgelenmiş, ama
adı ve etkisi uyuşmuyor. Silmeyi kamera/güne daralt ya da fonksiyon adını ve
docstring'i "tüm sayım geçmişini sıfırlar" diye netleştir. Bu ayarın
`.env.example`'da `false` olması iyi; **senin yerel `backend/.env`'inde `true`**
— Faz 0'dan sonra yerel DB'nin her döngüde silinmediğinden emin ol.

### 5.3 · Çok tür eğitimi (isteğe bağlı, ayrı iş kalemi)

`training/MULTISPECIES_DATA.md` yazılmış, `download_auth_sheep.py` ve
`download_open_images.py` hazır, `datasets/CattleEyeView Dataset/` indirilmiş —
ama veri hazırlama/eğitim henüz koşulmamış. Bu, envanter işinden **bağımsız**
bir iş kalemi; envanteri bitirmeyi bekletmemeli.

Model şu an yalnızca `sheep` için fine-tune edilmiş durumda. Envanter arayüzü
dört türü de sunduğu için, bu tamamlanana kadar `cattle/goat/horse` sayımının
temel model seviyesinde olduğu README'de ve Çiftlik sayfasında belirtilmeli.

---

## Faz 6 — Doküman ve sürüm

1. **`README.md`** — "Farm inventory" bölümü: bölge/grup kavramı, kamera
   bağlantısı, `EXTERNAL` bölgenin anlamı ve neden negatife düşebildiği,
   mutabakat akışı. Ekran akışı: Çiftlik → Kameralar → Panel.
2. **`docs/FARM-INVENTORY-PLAN.md`** — her maddenin karşısına durum işareti;
   2.2'de A yerine B seçildiyse gerekçesi.
3. **`models/README.md`** — tür kapsamı uyarısı (5.3).
4. **Commit stratejisi.** Tek dev commit yerine faz başına bir commit:
   `Fix inventory movement for external zones`, `Wire inventory alerts into
   Telegram and /api/status`, `Move farm translations into translations.ts`,
   `Cover the camera → inventory path with tests` … Böylece CI hangi fazın
   neyi bozduğunu gösterir.
5. **Sürüm.** Hepsi yeşil olunca `v1.1.0` etiketi (yeni özellik + migrasyon →
   minor). `docs/RELEASE.md`'deki akışı izle; `0010` (ve varsa `0011`)
   migrasyonu için geri alma notu ekle.

---

## Uygulama sırası ve bağımlılıklar

```
Faz 0  (5 dk)   ──►  yeşil taban, her şeyin ön koşulu
                      │
Faz 1  (yarım gün)   ├─► 1.1 kritik — envanter bunsuz çalışmaz
                      │   1.2 1.3 1.5 küçük, bağımsız
                      │   1.4 alarm  ──┐
                      ▼                │
Faz 2  (1 gün)   2.4 seed ─► 2.1 transfer UI                     
                 2.2 grup çakışması ◄──┘ (1.4 alarmını kullanır)
                 2.3 Telegram      ◄──┘
                      ▼
Faz 3  (yarım gün)   i18n birleştirme — Faz 2 UI'ları bittikten sonra,
                      yoksa aynı metinleri iki kez taşırsın
                      ▼
Faz 4  (yarım gün)   testler — Faz 1-3'ün davranışını kilitler
                      ▼
Faz 5  (ölçüme bağlı) vision performansı — bağımsız, paralel yürüyebilir
                      ▼
Faz 6  (2 saat)      doküman + v1.1.0
```

**En kısa "çalışır hale getir" yolu:** Faz 0 + 1.1 + 1.4. Bu üçü envanterin
sessizce yanlış çalışmasını durdurur; gerisi tamamlama ve cilalama.

## Kabul kriterleri (bitmiş sayılması için)

Orijinal planın altı kriteri, artık her biri bir testle:

- [x] Aynı kamera olayı ikinci kez stok değiştiremez
- [x] Bir geçişte kaynak ve hedef bölge toplamı korunur
- [x] Manuel düzeltme, nedeni ve yapan kullanıcı olmadan kaydedilemez
- [x] Kamera bağlantısı eksikken otomatik stok değişmez
- [x] Viewer hiçbir envanter verisini değiştiremez
- [ ] Yeniden başlatma ve video döngüsü stokları şişirmez *(mevcut testler dolaylı kanıtlıyor — `uq_event_crossing` + `uq_inventory_movement_source_event`; Faz 4'te doğrudan test eklenecek)*

Bu plandan eklenenler:

- [x] Temiz kurulumda ilk `IN` geçişi envanteri artırır *(1.1)*
- [x] Envanter kopukluğu sessiz kalmaz — Telegram + panel *(1.4)*
- [ ] Dört dilde hiçbir sayfada sabit İngilizce metin kalmaz *(Faz 3)*
- [x] `backend/.env` içeriği test sonucunu değiştirmez *(0.1)*
