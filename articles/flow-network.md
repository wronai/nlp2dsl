# FlowNetwork — Eksperymentalny Moduł LLM z Pattern-Based Routing

**Status projektu:** Eksperymentalny | **Język:** Python | **Zależności:** PyTorch

---

FlowNetwork to eksperymentalny moduł dla dużych modeli językowych, który łączy pattern-based flow routing z mechanizmami attention i pamięcią długoterminową. Główny cel to obsługa długich kontekstów przy niższym koszcie obliczeniowym niż standardowa pełna atencja.

## Podejście architektoniczne

Zamiast gęstych macierzy pełnej atencji FlowNetwork wykorzystuje zestaw wzorców (patterns) mieszanych wagami na każdy token. To podejście obniża liczbę parametrów i pozwala na bardziej efektywne przetwarzanie długich sekwencji.

Główne komponenty to FlowLayer generujący zredukowane, wielowymiarowe „flow patterns" i składający macierz przepływów token-do-token z batched sparsity (top-k). EnhancedFlowLayer rozszerza go o self/cross-attention i opcjonalną integrację z memory bankiem. ContextAwareFlowRouter adaptuje sparsity i routing w oparciu o cechy kontekstowe, stosując sliding windows dla długich sekwencji.

## Pamięć i bezpieczeństwo

FlowMemoryNetwork zapewnia bufor pamięci z bezpiecznymi aktualizacjami, mechanizmami odczytu i EMA update. Memory bank jest zarejestrowany jako buffer i aktualizowany w bloku `torch.no_grad()`, co zachowuje bezpieczeństwo autograd.

Moduł implementuje defensywne wywołania JIT, bezpieczne konwersje tensor-do-int oraz automatyczne dopasowanie liczby głów attention dzięki helperowi `adjust_num_heads`. Walidacja krytycznych parametrów (vocab_size, d_model, num_layers) chroni przed błędami konfiguracji.

## Warianty

FlowNetwork to główny wrapper łączący embeddingi, stos EnhancedFlowLayer i head do logits. EnhancedFlowTransformer to alternatywna integracja Flow + Transformer z automatyczną adaptacją wymiarów. Oba warianty można konfigurować i testować niezależnie.
