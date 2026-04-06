# DRM Module 6 Advanced — Dynamiczne Zarządzanie Regułami

**Status projektu:** Aktywny rozwój (v6.0) | **Język:** Python 3.8+ | **Zależności:** standardowa biblioteka

---

DRM Module 6 Advanced to kompletna biblioteka Pythona do zarządzania, wyszukiwania, optymalizacji i analizy reguł decyzyjnych. Wersja 6.0 wprowadza zaawansowane analizy i kompozycję reguł, zachowując pełną typizację i wydajność.

## Architektura reguł

Każda reguła to typ-bezpieczny obiekt `Rule` z jasno określonymi polami — typ, kategoria, tagi, priorytet, parametry, poziom złożoności. System obsługuje pięć poziomów złożoności: ATOMIC, SIMPLE, COMPOUND, COMPLEX i COMPOSITE, oraz trzy typy reguł: LOGICAL, HEURISTIC i HYBRID z walidacją semantyczną.

Reguły mogą tworzyć hierarchie rodzic-dziecko, co pozwala na kompozycję prostych reguł w złożone zachowania. Priority-based scheduling i optymalizacja kosztów wykonania zapewniają efektywne przetwarzanie nawet dużych zbiorów reguł.

## Wydajność i wyszukiwanie

Indeksy tagów, kategorii i poziomu złożoności umożliwiają wyszukiwanie w czasie O(1). System wykrywa duplikaty zarówno na poziomie semantycznym, jak i behawioralnym, analizując podobieństwo reguł. Optymalizacja kolejności wykonywania sortuje reguły od najprostszych do najbardziej złożonych.

## Analityka

Moduł oferuje zaawansowane analizy obejmujące rozkłady typów, kategorii i tagów, trendy wydajności, wzorce użycia i metryki efektywności. Wskaźnik dywersyfikacji pomaga ocenić pokrycie przestrzeni reguł. Wersja zintegrowana (DRM v6 Integrated) łączy najlepsze cechy modułów 5 i 6, dodając pełny cykl uczenia z replay bufferem, rozwiązywaniem konfliktów i Bayesowskimi aktualizacjami wag.

## Integracja

Funkcje eksportu i importu ułatwiają integrację z innymi systemami. Przykładowy skrypt `demo()` pozwala zapoznać się z możliwościami modułu w 30 sekund.
