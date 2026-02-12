# Leaguepedia API Authentication

Um höhere Rate Limits zu bekommen und MWException-Fehler zu vermeiden, kannst du dich mit Bot-Credentials authentifizieren.

## Schritt 1: Bot-Credentials erstellen

1. Gehe zu: https://lol.fandom.com/wiki/Special:BotPasswords
2. Falls du noch nicht eingeloggt bist, melde dich mit deinem Fandom-Account an
3. Klicke auf "Create a new bot password"
4. **Bot Name**: Wähle einen Namen (z.B. `DataImport`)
5. **Grants**: Wähle mindestens:
   - ✓ Basic rights (erforderlich)
   - ✓ High-volume editing
   - ✓ Edit existing pages
6. Klicke auf "Create"
7. **WICHTIG**: Kopiere den generierten Username und Password SOFORT (sie werden nur einmal angezeigt!)

## Schritt 2: Credentials als Environment Variables setzen

### Windows (PowerShell):
```powershell
$env:LEAGUEPEDIA_BOT_USERNAME = "DeinUsername@DataImport"
$env:LEAGUEPEDIA_BOT_PASSWORD = "dein_generiertes_password"
```

### Windows (CMD):
```cmd
set LEAGUEPEDIA_BOT_USERNAME=DeinUsername@DataImport
set LEAGUEPEDIA_BOT_PASSWORD=dein_generiertes_password
```

### Linux/Mac:
```bash
export LEAGUEPEDIA_BOT_USERNAME="DeinUsername@DataImport"
export LEAGUEPEDIA_BOT_PASSWORD="dein_generiertes_password"
```

### Permanent (Windows):
Füge die Variablen zu den System-Umgebungsvariablen hinzu:
1. Systemsteuerung → System → Erweiterte Systemeinstellungen
2. Umgebungsvariablen
3. Neue Benutzervariable hinzufügen

### Permanent (Linux/Mac):
Füge zu `~/.bashrc` oder `~/.zshrc` hinzu:
```bash
export LEAGUEPEDIA_BOT_USERNAME="DeinUsername@DataImport"
export LEAGUEPEDIA_BOT_PASSWORD="dein_generiertes_password"
```

## Schritt 3: Import testen

```bash
cd /home/user/lol-elo-system
python scripts/import_tier1_data.py
```

Du solltest sehen:
```
[OK] Authenticated as DeinUsername@DataImport
```

## Ohne Authentication

Falls du keine Bot-Credentials erstellst, läuft das Programm trotzdem, aber mit niedrigeren Rate Limits:
- Unauthenticated: ~200 requests/hour
- Authenticated: ~5000 requests/hour

## Troubleshooting

### "Login failed: WrongToken"
Die Session ist abgelaufen. Starte das Programm neu.

### "Login failed: Failed"
Username oder Password falsch. Überprüfe die Credentials.

### "Rate limited"
Zu viele Anfragen. Warte 10-15 Minuten oder authentifiziere dich.

## Sicherheit

**⚠️ WICHTIG**:
- Teile dein Bot-Password NIE mit anderen!
- Committe das Password NICHT in Git!
- Die Environment Variables sind nur für deine lokale Maschine
