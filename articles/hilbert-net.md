# HilbertNet — Uniwersalna Sieć Neuronowa z Krzywą Hilberta

**Status projektu:** Stabilny | **Język:** Python 3.11+ | **Zależności:** numpy, scipy

---

HilbertNet to samodzielny skrypt Pythona łączący obliczenia przestrzenne na krzywej Hilberta z automatyzacją logiki, prostymi maszynami uczącymi i interaktywnym shellem. Całość zamknięta w jednym pliku — bez tradycyjnej instalacji.

## Czym jest krzywa Hilberta w kontekście sieci neuronowej

Krzywa Hilberta to krzywa wypełniająca przestrzeń, która mapuje dane jednowymiarowe na wielowymiarową siatkę zachowując lokalność. HilbertNet wykorzystuje 32-bitową krzywą Hilberta rzędu 16 jako fundament obliczeń przestrzennych, co pozwala na efektywne przetwarzanie danych z zachowaniem relacji sąsiedztwa.

## Zintegrowane możliwości

Moduł łączy kilka warstw funkcjonalności. Obliczenia przestrzenne na krzywej Hilberta stanowią fundament. Automatyzacja logiki obejmuje reguły, warunki i propagację — system sam decyduje o wykonaniu na podstawie zdefiniowanych zasad. Proste maszyny uczące realizują klasyfikację, backpropagation i reinforcement learning. Mechanizm zapisu i odczytu w formacie JSON pozwala na persystencję modeli.

Interaktywny shell (REPL) udostępnia wiele przydatnych poleceń do eksploracji i testowania. Tryb demo (`python hilbertnet.py demo1`) pozwala szybko zapoznać się z możliwościami bez pisania kodu.

## Zastosowania

HilbertNet nadaje się do eksperymentów z przestrzennymi reprezentacjami danych, prototypowania systemów regułowych z komponentem uczenia maszynowego oraz jako narzędzie edukacyjne łączące koncepcje z geometrii obliczeniowej i sieci neuronowych.
