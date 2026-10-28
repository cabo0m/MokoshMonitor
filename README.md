# MokoshMonitor

Lokalny program dla Windows monitorujący pojawianie się nowych produktów w sklepie Mokosh. Python, Tkinter, SQLite. Bez serwera, VPS i zewnętrznych agentów AI.

## Uruchomienie

1. Zainstaluj Python 3.10+ (wraz z Python Launcher `py`).
2. Uruchom `git clone https://github.com/cabo0m/MokoshMonitor.git` i wejdź do katalogu `MokoshMonitor`.
3. Uruchom `start.bat`, który sam tworzy `.venv`, instaluje zależności i tworzy lokalną konfigurację.
4. W aplikacji wybierz **Sprawdź teraz**. Pierwsze pobranie ustanawia bazę bez alarmów.
5. **Start** włącza cykl kontroli co 15 minut, **Stop** zatrzymuje go. Test alertu nie zmienia bazy.

**Tryb demo:** kliknij **Symuluj nowy produkt**, aby dodać fikcyjną pozycję do tabeli i dziennika. Symulacja działa bez połączenia ze sklepem i nie zapisuje produktu w SQLite. **Test alertu** pokazuje wpis testowy w dzienniku oraz opcjonalnie wysyła test na Telegram.

Aplikacja działa tylko przy włączonym komputerze i otwartym oknie. Realny monitoring wymaga dostępu do Internetu.

## Powiadomienia

Ekran i dziennik pokazują nowe produkty. Opcjonalnie w prywatnym pliku `config.json` ustaw `telegram_bot_token` i `telegram_chat_id`. Otrzymasz alert z nazwą i linkiem. Nie publikuj tokenów.

## Mechanizm

Publiczny endpoint `/products.json` (gdy jest dostępny), w przeciwnym razie strona `/collections/all`. Nowe adresy produktów porównywane są ze stanem zapisanym w `monitor.db`. Błędy pobierania zapisywane są w bazie.

## Ograniczenia MVP

To prototyp. Nie potwierdzono jeszcze integracji na żywo z mokosh.pl. Zmiany struktury strony, zabezpieczenia antybotowe lub niepełna paginacja mogą zakłócać pracę. Monitor wykrywa nowe produkty, nie powrót na stan magazynowy ani zmiany cen. Alerty Telegram nie mają trwałej kolejki ponowień.

Przygotowane przez [MorenaTech.work](https://morenatech.work).

## Gotowa aplikacja Windows (.exe)

W zakładce [Releases](https://github.com/cabo0m/MokoshMonitor/releases) znajdziesz (po pomyślnym zbudowaniu wydania) `MokoshMonitor.exe` oraz `MokoshMonitor-Windows.zip`. Pobierz ZIP, rozpakuj i uruchom EXE. Python nie jest wymagany. Baza i konfiguracja tworzą się lokalnie obok programu.

### Tworzenie wydania

Wejdź w **Actions → Build Windows demo and Release → Run workflow**, zostaw tag `v0.1.0-demo` i uruchom. Workflow buduje EXE na Windows, sprawdza podstawową składnię/import, tworzy ZIP i publikuje *prerelease*. Działa też przy wypchnięciu taga `v*`. Budowanie i status publikacji zweryfikuj w zakładce Actions. Testy live integracji ze sklepem i ręczny smoke test aplikacji pozostają do wykonania.
