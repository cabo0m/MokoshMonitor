# MokoshMonitor

Lokalny program dla Windows monitorujący pojawianie się nowych produktów w sklepie Mokosh. Python, Tkinter, SQLite. Bez serwera, VPS i zewnętrznych agentów AI.

## Uruchomienie

1. Zainstaluj Python 3.10+ (wraz z Python Launcher `py`).
2. Pobierz repozytorium (Code → Download ZIP) i rozpakuj.
3. Uruchom `start.bat`, który instaluje zależności i kopiuje przykładową konfigurację.
4. W aplikacji wybierz **Sprawdź teraz**. Pierwsze pobranie ustanawia bazę bez alarmów.
5. **Start** włącza cykl kontroli co 5 minut, **Stop** zatrzymuje go. Test alertu nie zmienia bazy.

Aplikacja działa tylko przy włączonym komputerze, otwartym oknie i dostępie do Internetu.

## Powiadomienia

Ekran i dziennik pokazują nowe produkty. Opcjonalnie w prywatnym pliku `config.json` ustaw `telegram_bot_token` i `telegram_chat_id`. Otrzymasz alert z nazwą i linkiem. Nie publikuj tokenów.

## Mechanizm

Publiczny endpoint `/products.json` (gdy jest dostępny), w przeciwnym razie strona `/collections/all`. Nowe adresy produktów porównywane są ze stanem zapisanym w `monitor.db`. Błędy pobierania zapisywane są w bazie.

## Ograniczenia MVP

To prototyp. Nie potwierdzono jeszcze integracji na żywo z mokosh.pl. Zmiany struktury strony, zabezpieczenia antybotowe lub niepełna paginacja mogą zakłócać pracę. Monitor wykrywa nowe produkty, nie powrót na stan magazynowy ani zmiany cen. Alerty Telegram nie mają trwałej kolejki ponowień.

Przygotowane przez [MorenaTech.work](https://morenatech.work).
