# Simplified RAG Interface - Testing Guide

> **Source**: Originally located at `DashAI/front/src/pages/generative/simplified-RAG/TESTING_GUIDE.md`. Moved here on 2026-06-01 as part of documentation consolidation.

## Acceso a la Nueva Interfaz

**URL**: `http://localhost:3000/app/generative/simplified-rag`

O desde el código:
```bash
navigate('/app/generative/simplified-rag')
```

## Flujo de Uso

### Pantalla Única: Configuración Simplified RAG (Single Scroll)
```
Pantalla: SimplifiedSessionSetup

Sección: Session Details
├─ Campo: Session Name * (requerido)
└─ Campo: Description (opcional)

Sección: Select Documents
└─ Selector: DocumentSelector * (reutiliza DocumentSelector existente)

┌─ Accordion 1: Chunking Strategy ─────────────────┐
│ Presets:                                          │
│   ◉ Paragraph length (500 tokens)                │
│   ◯ Page chunk (2000 tokens)                    │
│   ◯ Custom configuration                        │
│                                                  │
│ Current: chunk_size=500, overlap=50             │
│ [↗ Open Advanced Configuration]                 │
└──────────────────────────────────────────────────┘

┌─ Accordion 2: Retriever Model ────────────────────┐
│ Paradigm: [SparseRetriever ▼]                    │
│ Model: [BM25 ▼]  (si hay múltiples opciones)   │
│                                                  │
│ Info: SparseRetriever - Dense Vector retrieval │
│ [↗ Open Advanced Configuration]                 │
└──────────────────────────────────────────────────┘

┌─ Accordion 3: Language Model (LLM) ──────────────┐
│ [GPT-4 ▼]                                       │
│                                                  │
│ Info: OpenAI's GPT-4 model                      │
│ [↗ Open Advanced Configuration]                 │
└──────────────────────────────────────────────────┘

┌─ Accordion 4: Prompt Template ────────────────────┐
│ [Default Prompt ▼]                              │
│                                                  │
│ Info: Standard RAG prompt template              │
│ [↗ Open Advanced Configuration]                 │
└──────────────────────────────────────────────────┘

Botones: [Cancel] [Save Session]
```

---

## Características de la Nueva Interfaz

### ✨ Simplificada
- UI clara con opciones preestablecidas
- Menos pasos (1 pantalla en lugar de 5)
- Información condensada

### 🔧 Configurable
- Botones "Open Advanced Configuration" para cada sección
- Modales con acceso completo al FormSchema original
- Preserva toda la funcionalidad de los componentes existentes

### 📦 Reutilizable
- Reutiliza componentes existentes:
  - DocumentSelector
  - ChunkingConfigurationStep
  - RetrieverConfigurationStep
  - GeneratorConfigurationStep
  - PromptSelectionTable

### 🎨 Responsive
- Layout 3-panel igual que RAGHomePage
- SessionBar a la izquierda
- Panel derecho con explicación básica de RAG (sin DocumentsBar)
- Scroll central con secciones colapsibles

---

## Flujo de Datos

```
SimplifiedSessionSetup
  ↓
  sessionData: {
    name: "My RAG Session",
    description: "Optional description",
    documents: [1, 2, 3],
    parameters: {
      chunking_model: {
        component: "SimpleChunker",
        params: { chunk_size: 500, chunk_overlap: 50 }
      },
      retriever_model: {
        component: "BM25",
        params: { ... }
      },
      generator_model: {
        component: "GPT-4",
        params: { ... }
      },
      prompt_id: 1
    }
  }
  ↓
  createRAGSession(sessionData)
```

---

## Testing Checklist

- [ ] Navegar a `/app/generative/simplified-rag`
- [ ] Rellenar nombre de sesión
- [ ] Rellenar descripción (opcional)
- [ ] Seleccionar documentos
- [ ] Verificar cada sección colapsible
- [ ] Hacer click en "Open Advanced Configuration" de cada sección
- [ ] Verificar que se abre el modal correcto
- [ ] Completar configuraciones
- [ ] Click "Save Session"
- [ ] Verificar que la sesión se crea correctamente
- [ ] Comparar con interfaz wizard original

---

## Comparación: Original vs Simplified

| Aspecto | Original Wizard | Simplified |
|---------|-----------------|-----------|
| Steps | 5 pasos separados | 1 pantalla |
| Layout | Stepper/Dialog | Accordions/Scroll |
| Documentos | Step 0 | Sección "Select Documents" |
| Chunking | Step 1 (wizard) | Sección 1 (accordion) |
| Retriever | Step 2 (wizard) | Sección 2 (accordion) |
| Generator | Step 3 (wizard) | Sección 3 (accordion) |
| Prompt | Step 4 (wizard) | Sección 4 (accordion) |
| Avanzado | Inline FormSchema | Modal con FormSchema |

---

## Archivo de Prueba

Puedes navegar directamente con:

```javascript
// En cualquier componente con acceso a navigate
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

// Para ir a simplified-rag
navigate('/app/generative/simplified-rag');

// Para ir a original RAG setup (NewSessionModal)
navigate('/app/generative/rag/sessions');
```

---

## Ubicación de Archivos

```
/src/pages/generative/simplified-RAG/
├── SimplifiedRAGPage.jsx                    (página principal)
├── SimplifiedSessionSetup.jsx               (pantalla única)
├── sections/
│   ├── ChunkingSection.jsx
│   ├── RetrieverSection.jsx
│   ├── GeneratorSection.jsx
│   ├── PromptSection.jsx
│   └── index.js
├── advanced/
│   ├── ChunkingAdvancedModal.jsx
│   ├── RetrieverAdvancedModal.jsx
│   ├── GeneratorAdvancedModal.jsx
│   ├── PromptAdvancedModal.jsx
│   └── index.js
```

---

## Próximos Pasos

1. **Testing**: Verificar que la interfaz funciona correctamente
2. **Ajustes de UX**: Refinar estilos si es necesario
3. **Comparación**: Usar ambas interfaces para verificar paridad de funcionalidad
4. **Migración**: Considerar deprecar el wizard original si la simplified es superior
