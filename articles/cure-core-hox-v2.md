# CureCoreHox v2 — Warstwa Ochrony Danych z Korekcją Błędów Bitowych

**Status projektu:** Stabilny | **Język:** Python | **Zależności:** standardowa biblioteka (zlib, random, argparse, json)

---

CureCoreHox v2 to samodzielny moduł Pythona łączący kilka mechanizmów ochrony i naprawy danych bitowych w jednym pliku. Może działać zarówno jako narzędzie CLI, jak i importowana biblioteka w większym projekcie.

## Mechanizmy ochrony

Moduł integruje sześć wzajemnie uzupełniających się warstw bezpieczeństwa danych. Kodowanie Zeckendorfa (Fibitrix) zapewnia unikalne binarne przedstawienie liczby bez dwóch kolejnych jedynek, co minimalizuje „kroki" bitowe i ułatwia detekcję uszkodzeń. CRC-32 dodaje sumę kontrolną dla całej liczby, służąc jako dodatkowa warstwa detekcji. Triple Modular Redundancy (TMR) przechowuje dane trzykrotnie i stosuje głosowanie większościowe, co zapewnia tolerancję na pojedyncze błędy.

Dla bardziej zaawansowanych przypadków moduł oferuje pojedynczą korekcję bitową — wyszukiwanie najlepszego jednobitowego flipu — oraz BFS-based multi-bit correction, czyli eksplorację drzewową do głębokości trzech bitów. Mechanizm snapshot/rollback pozwala przywrócić ostatni poprawny stan danych w sytuacjach krytycznych.

## Tryby użycia

Jako narzędzie CLI uruchamiane przez `python cure_core_hox_v2.py` moduł oferuje szybkie demo i eksperymenty symulacyjne z losowymi liczbami, flipami bitowymi i statystykami. Jako importowany moduł udostępnia pełne API do kodowania, walidacji i naprawy danych w dowolnym projekcie Python.

## Zastosowania

Moduł nadaje się do ochrony danych krytycznych, systemów wymagających fail-safe, testowania i benchmarkingu algorytmów korekcji błędów. Zero zewnętrznych zależności czyni go łatwym do wdrożenia w dowolnym środowisku.
