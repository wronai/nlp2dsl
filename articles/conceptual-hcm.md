# ConceptualHCM — Hierarchiczna Kompresja Semantyczna dla LLM

**Status projektu:** Aktywny rozwój | **Język:** Python | **Zależności:** numpy, opcjonalnie sentence-transformers

---

ConceptualHCM to moduł Pythona, który zamiast przechowywać pełny tekst rozmowy buduje graf konceptów. Pozwala na inteligentne kompresowanie konwersacji w symboliczne reprezentacje — idealne rozwiązanie problemu ograniczonego okna kontekstowego w modelach językowych.

## Jak to działa

System opiera się na czterech głównych komponentach. `Concept` to węzeł grafu reprezentujący pojedynczy koncept z jego esencją, słowami kluczowymi, wagą, częstotliwością i embeddingami. `ConceptGraph` to sieć węzłów i krawędzi, która pozwala na aktywację podgrafów, agregację i pobieranie najważniejszych konceptów. `ConceptExtractor` łączy ekstrakcję NER-like, keyword extraction oraz embedding-based linking. `ConceptualHCM` spina wszystko jako główny manager — przyjmuje tury rozmowy, buduje graf, obsługuje zapytania i generuje zoptymalizowane prompty.

## Główne możliwości

Moduł pozwala na szybkie kompresowanie długich konwersacji do zwięzłych, symbolicznych reprezentacji. Wyszukiwanie semantyczne na grafie konceptów zwraca najbardziej istotne fragmenty kontekstu dla danego zapytania. Rozpakowywanie kontekstu generuje optymalny prompt dla modelu LLM. Serializacja i persystencja pozwalają zapisywać i odtwarzać pełną historię rozmów.

## Zastosowania

ConceptualHCM jest szczególnie przydatny w systemach wymagających długiej pamięci konwersacyjnej — chatboty, asystenci, systemy analizy dokumentów — wszędzie tam, gdzie pełny tekst nie mieści się w oknie kontekstowym LLM, ale kontekst musi być zachowany.
