# Sistema de Navegação Fuzzy para Robô Móvel

Sistema de navegação autônoma para robô móvel utilizando Lógica Fuzzy baseado no artigo **"Shortest Path Planning and Efficient Fuzzy Logic Control of Mobile Robots in Indoor Static and Dynamic Environments"**.

## 📋 Descrição

Este projeto implementa um controlador fuzzy eficiente (EFLC) para navegação de robôs móveis em ambientes com obstáculos estáticos. O sistema utiliza lógica fuzzy para tomar decisões suaves e inteligentes sobre a direção do movimento, permitindo que o robô navegue até um alvo evitando obstáculos.

## 🎯 Características

- **Sistema Fuzzy Completo**: Implementa fuzzificação, inferência e defuzzificação
- **19 Regras Fuzzy**: Baseadas no artigo científico, organizadas por prioridade
- **Navegação Suave**: Movimentos graduais sem mudanças bruscas
- **Detecção de Obstáculos**: Sistema de raycast em 3 direções (frontal, esquerda, direita)
- **Interface Gráfica**: Visualização em tempo real da trajetória do robô

## 🚀 Como Executar

### Requisitos
- Python 3.7+
- NumPy
- Matplotlib
- scikit-fuzzy

### Instalação
```bash
pip install numpy matplotlib scikit-fuzzy
```

### Execução
```bash
python fuzzyPathWay.py
```

## 📚 Documentação

- **GUIA_APRESENTACAO_FUZZY.md**: Guia completo para apresentação do sistema
- **ANALISE_LOGICA_FUZZY.md**: Análise técnica detalhada do código

## 🔬 Baseado em

**Artigo:** "Shortest Path Planning and Efficient Fuzzy Logic Control of Mobile Robots in Indoor Static and Dynamic Environments"

**Componentes Implementados:**
- EFLC (Efficient Fuzzy Logic Controller)
- Sistema de inferência fuzzy tipo Mamdani
- Defuzzificação por centróide
- 19 regras fuzzy priorizadas

## 📊 Sistema Fuzzy

### Entradas
- Distância frontal ao obstáculo (0-100 cm)
- Distância esquerda (0-100 cm)
- Distância direita (0-100 cm)
- Ângulo ao alvo (-180° a +180°)

### Saída
- Ângulo de correção (-90° a +90°)

### Conjuntos Fuzzy
- **Distâncias**: muito_perto, perto, médio, longe
- **Ângulo**: esquerda_forte, esquerda, frente, direita, direita_forte
- **Correção**: esquerda_forte, esquerda, reto, direita, direita_forte

## 🎮 Controles

- **Botão "Reiniciar"**: Reinicia a simulação com novos obstáculos e alvo

## 📝 Licença

Este projeto é para fins educacionais e de pesquisa.

