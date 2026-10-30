# 📡 Hackathon Radar

Başvurusu açık **hackathon, ideathon, datathon ve yarışmaları** tek sayfada toplayan, her gün GitHub Actions ile kendini yenileyen statik site.

## Kaynaklar

| Kaynak | Yöntem | Anahtar gerekir mi? |
|---|---|---|
| Devpost | Public JSON API | Hayır |
| MLH | Sayfadaki gömülü JSON | Hayır |
| Luma | Discover API (`hackathon`, `datathon`… araması + 9 Türk şehri) | Hayır |
| Coderspace | JSON-LD + detay sayfasından son başvuru | Hayır |
| Techcareer.net | Next.js verisi (`/hackathon`, `/datathon`, `/ideathon`) | Hayır |
| Youthall, Anbean Kampüs | HTML kartları (Anbean hackathon/ideathon/yarışma kategorileri), son başvuru detay sayfasından doğrulanır | Hayır |
| TEKNOFEST | Yarışma kartları, sadece başvurusu açık olanlar | Hayır |
| Kaggle | Kaggle API | `KAGGLE_USERNAME`, `KAGGLE_KEY` |
| LinkedIn, Instagram, X, TikTok, üniversiteler (edu.tr), Kommunity, GDG, Patika, BTK Akademi, Medium… | **Claude Code GitHub Action**: web araması yapar, açık yarışmaları ayıklar, `data/claude_found.json` dosyasına yazar | `CLAUDE_CODE_OAUTH_TOKEN` (Claude Pro/Max aboneliği, API ücreti yok) |
| Aynı kaynaklar (alternatif) | Google araması (Serper.dev) + opsiyonel Claude API ayıklaması | `SERPER_API_KEY`, `ANTHROPIC_API_KEY` |

Instagram/TikTok/X/LinkedIn doğrudan kazımayı engellediği için bu gönderiler arama motoru üzerinden bulunur.

## Kurulum (GitHub)

1. Claude abonelik token'ını oluştur ve secret olarak ekle:
   ```bash
   claude setup-token
   gh secret set CLAUDE_CODE_OAUTH_TOKEN -R ayse-solmaz/hackathon-radar
   ```
   Opsiyonel secret'lar: `KAGGLE_USERNAME`, `KAGGLE_KEY`, `SERPER_API_KEY`, `ANTHROPIC_API_KEY`.
2. **Settings → Pages → Source: GitHub Actions**
3. **Actions → Günlük güncelleme ve yayın → Run workflow**

Workflow her gün 07:00'de (TR) çalışır, veriyi `site/data/events.json` olarak commit'ler ve Pages'e yayınlar.

## Yerelde çalıştırma

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m scraper.run
python -m http.server 8765 --directory site
```

## Yeni kaynak eklemek

`scraper/sources.py` içine `list[Event]` döndüren bir fonksiyon yaz ve `ALL` sözlüğüne ekle. Sosyal/web sorguları `scraper/social.py` → `QUERIES`.
