import numpy as np
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import random
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ==============================================================
# CONFIGURAÇÃO DO AMBIENTE
# ==============================================================

MAP_SIZE = 6.0
ROBOT_RADIUS = 0.25
MARGEM_COLISAO = 0.01  # Margem de segurança reduzida (5cm ao invés de usar raio completo)
VELOCIDADE = 0.3
DT = 0.1

# ==============================================================
# GERAÇÃO DE OBSTÁCULOS
# ==============================================================

def gerar_obstaculos_aleatorios():
    """Gera obstáculos aleatórios no mapa"""
    # Paredes fixas
    obstaculos = [
        [0, MAP_SIZE, 0, 0.25],                   # parede inferior
        [0, MAP_SIZE, MAP_SIZE-0.25, MAP_SIZE],   # parede superior
        [0, 0.25, 0, MAP_SIZE],                   # parede esquerda
        [MAP_SIZE-0.25, MAP_SIZE, 0, MAP_SIZE],   # parede direita
    ]
    
    # Gera 2-4 obstáculos aleatórios
    num_obstaculos = 10
    tentativas = 0
    max_tentativas = 100
    
    while len(obstaculos) < 4 + num_obstaculos and tentativas < max_tentativas:
        largura = random.uniform(0.3, 0.5)
        altura = random.uniform(0.3, 0.5)
        margem = 0.5
        x_min = random.uniform(margem, MAP_SIZE - margem - largura)
        y_min = random.uniform(margem, MAP_SIZE - margem - altura)
        x_max = x_min + largura
        y_max = y_min + altura
        
        # Verifica se não está muito próximo do ponto inicial
        dist_inicial = np.hypot((x_min + x_max)/2 - 0.5, (y_min + y_max)/2 - 0.5)
        if dist_inicial < 1.0:
            tentativas += 1
            continue
        
        # Verifica colisão com outros obstáculos
        colide_outro = False
        for obs_existente in obstaculos:
            if not (x_max < obs_existente[0] or x_min > obs_existente[1] or 
                   y_max < obs_existente[2] or y_min > obs_existente[3]):
                colide_outro = True
                break
        
        if not colide_outro:
            obstaculos.append([x_min, x_max, y_min, y_max])
        
        tentativas += 1
    
    return obstaculos

OBSTACULOS = []

# ==============================================================
# DETECÇÃO DE OBSTÁCULOS
# ==============================================================

def colide(x, y):
    """Verifica se a posição colide com algum obstáculo"""
    # Usa margem reduzida para permitir chegar mais perto
    margem = MARGEM_COLISAO
    for obs in OBSTACULOS:
        if (obs[0] - margem) <= x <= (obs[1] + margem) and \
           (obs[2] - margem) <= y <= (obs[3] + margem):
            return True
    return False

def raycast(x, y, angulo):
    """
    Lança um raio na direção especificada e retorna a distância ao obstáculo
    Retorna distância em cm (0-100)
    Usa margem reduzida para detectar obstáculos mais próximos
    """
    dist = 0.0
    passo = 0.01
    
    while dist < MAP_SIZE:
        px = x + dist * np.cos(angulo)
        py = y + dist * np.sin(angulo)
        
        # Verifica colisão com margem reduzida diretamente
        margem = MARGEM_COLISAO
        colidiu = False
        for obs in OBSTACULOS:
            if (obs[0] - margem) <= px <= (obs[1] + margem) and \
               (obs[2] - margem) <= py <= (obs[3] + margem):
                colidiu = True
                break
        
        if colidiu:
            return dist * 100  # converte para cm
        
        dist += passo
    
    return 100.0  # máximo

# ==============================================================
# SISTEMA FUZZY EFICIENTE (EFLC) - Baseado no artigo
# ==============================================================

# Universos de discurso
dist_frontal_universe = np.arange(0, 101, 1)  # 0-100 cm
dist_lateral_universe = np.arange(0, 101, 1)  # 0-100 cm
angulo_alvo_universe = np.arange(-180, 181, 1)  # -180 a 180 graus
angulo_saida_universe = np.arange(-90, 91, 1)  # -90 a 90 graus

# Variáveis de entrada
dist_frontal = ctrl.Antecedent(dist_frontal_universe, 'dist_frontal')
dist_esquerda = ctrl.Antecedent(dist_lateral_universe, 'dist_esquerda')
dist_direita = ctrl.Antecedent(dist_lateral_universe, 'dist_direita')
angulo_alvo = ctrl.Antecedent(angulo_alvo_universe, 'angulo_alvo')

# Variável de saída
angulo_correcao = ctrl.Consequent(angulo_saida_universe, 'angulo_correcao', 
                                  defuzzify_method='centroid')

# Funções de pertinência para DISTÂNCIA FRONTAL
dist_frontal['muito_perto'] = fuzz.trimf(dist_frontal_universe, [0, 0, 10])
dist_frontal['perto'] = fuzz.trimf(dist_frontal_universe, [5, 15, 25])
dist_frontal['medio'] = fuzz.trimf(dist_frontal_universe, [20, 35, 50])
dist_frontal['longe'] = fuzz.trapmf(dist_frontal_universe, [40, 60, 100, 100])

# Funções de pertinência para DISTÂNCIA LATERAL
# Ajustadas para ser menos sensível - só reage quando realmente muito próximo
for var in [dist_esquerda, dist_direita]:
    var['muito_perto'] = fuzz.trimf(dist_lateral_universe, [0, 0, 8])  # Reduzido de 15 para 8cm
    var['perto'] = fuzz.trimf(dist_lateral_universe, [5, 15, 25])  # Reduzido de 10-25-40
    var['medio'] = fuzz.trimf(dist_lateral_universe, [20, 35, 55])  # Ajustado
    var['longe'] = fuzz.trapmf(dist_lateral_universe, [45, 60, 100, 100])  # Ajustado

# Funções de pertinência para ÂNGULO AO ALVO
angulo_alvo['esquerda_forte'] = fuzz.trimf(angulo_alvo_universe, [-180, -135, -90])
angulo_alvo['esquerda'] = fuzz.trimf(angulo_alvo_universe, [-90, -45, 0])
angulo_alvo['frente'] = fuzz.trimf(angulo_alvo_universe, [-30, 0, 30])
angulo_alvo['direita'] = fuzz.trimf(angulo_alvo_universe, [0, 45, 90])
angulo_alvo['direita_forte'] = fuzz.trimf(angulo_alvo_universe, [90, 135, 180])

# Funções de pertinência para SAÍDA
angulo_correcao['esquerda_forte'] = fuzz.trimf(angulo_saida_universe, [-90, -60, -30])
angulo_correcao['esquerda'] = fuzz.trimf(angulo_saida_universe, [-45, -20, 0])
angulo_correcao['reto'] = fuzz.trimf(angulo_saida_universe, [-15, 0, 15])
angulo_correcao['direita'] = fuzz.trimf(angulo_saida_universe, [0, 20, 45])
angulo_correcao['direita_forte'] = fuzz.trimf(angulo_saida_universe, [30, 60, 90])

# ==============================================================
# REGRAS FUZZY - Baseadas no artigo
# ==============================================================

def inicializar_sistema_fuzzy():
    """Inicializa o sistema fuzzy EFLC"""
    regras = []
    
    # PRIORIDADE 1: Evitar obstáculos muito próximos à frente
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & 
                            dist_esquerda['longe'] & dist_direita['perto'], 
                            angulo_correcao['esquerda_forte']))
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & 
                            dist_esquerda['perto'] & dist_direita['longe'], 
                            angulo_correcao['direita_forte']))
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & 
                            dist_esquerda['medio'] & dist_direita['medio'], 
                            angulo_correcao['esquerda']))  # Default: esquerda
    
    # PRIORIDADE 2: Evitar obstáculos próximos à frente
    regras.append(ctrl.Rule(dist_frontal['perto'] & 
                            dist_esquerda['longe'] & dist_direita['medio'], 
                            angulo_correcao['esquerda']))
    regras.append(ctrl.Rule(dist_frontal['perto'] & 
                            dist_esquerda['medio'] & dist_direita['longe'], 
                            angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['perto'] & 
                            dist_esquerda['longe'] & dist_direita['longe'], 
                            angulo_correcao['esquerda']))
    
    # PRIORIDADE 3: Navegar em direção ao alvo quando há espaço médio
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['frente'], 
                            angulo_correcao['reto']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['esquerda'], 
                            angulo_correcao['esquerda']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['direita'], 
                            angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['esquerda_forte'], 
                            angulo_correcao['esquerda_forte']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['direita_forte'], 
                            angulo_correcao['direita_forte']))
    
    # PRIORIDADE 4: Navegar diretamente ao alvo quando há muito espaço
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['frente'], 
                            angulo_correcao['reto']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['esquerda'], 
                            angulo_correcao['esquerda']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['direita'], 
                            angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['esquerda_forte'], 
                            angulo_correcao['esquerda_forte']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['direita_forte'], 
                            angulo_correcao['direita_forte']))
    
    # PRIORIDADE 5: Ajuste lateral APENAS quando obstáculo muito próximo nas laterais E espaço frontal limitado
    # Não ajusta se há muito espaço frontal - permite passar mesmo com obstáculo lateral
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_esquerda['muito_perto'], 
                            angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_direita['muito_perto'], 
                            angulo_correcao['esquerda']))
    
    sistema_fuzzy = ctrl.ControlSystem(regras)
    return ctrl.ControlSystemSimulation(sistema_fuzzy)

# Inicializa sistema fuzzy globalmente
simulador_fuzzy = None

def controlador_fuzzy_eflc(sensores, angulo_alvo_deg, theta_atual=None):
    """
    Controlador Fuzzy Eficiente (EFLC) baseado no artigo
    
    Lógica simplificada:
    - Se há espaço frontal suficiente (> 20cm), pode continuar na direção do movimento
    - Obstáculos laterais só importam se estão MUITO próximos (< 8cm) E espaço frontal limitado
    - Só desvia se obstáculo está realmente bloqueando a direção do movimento
    
    Args:
        sensores: dicionário com distâncias em cm (frontal, esquerda, direita)
        angulo_alvo_deg: ângulo ao alvo em graus (-180 a 180)
        theta_atual: direção atual do movimento em radianos (opcional)
    
    Returns:
        ângulo de correção em graus (-90 a 90)
    """
    global simulador_fuzzy
    
    if simulador_fuzzy is None:
        simulador_fuzzy = inicializar_sistema_fuzzy()
    
    d_f = sensores['frontal']
    d_e = sensores['esquerda']
    d_d = sensores['direita']
    
    # REGRA 1: PRIORIDADE ABSOLUTA - Obstáculo muito próximo À FRENTE (< 10cm)
    # SEMPRE desvia, não importa a direção do movimento
    if d_f < 10:
        if d_d > d_e + 3:
            return 60  # Desvia forte à direita
        elif d_e > d_d + 3:
            return -60  # Desvia forte à esquerda
        else:
            return 45 if angulo_alvo_deg > 0 else -45
    
    # REGRA 2: Se há espaço frontal suficiente (> 20cm), pode continuar
    # IGNORA obstáculos laterais a menos que estejam MUITO próximos (< 8cm)
    if d_f > 20:
        # Verifica se obstáculo lateral está MUITO próximo e pode bloquear
        # Só considera se está quase encostando (< 8cm)
        lateral_muito_proximo = (d_e < 8) or (d_d < 8)
        
        if not lateral_muito_proximo:
            # Espaço frontal OK e laterais OK - navega ao alvo
            correcao = np.clip(angulo_alvo_deg * 0.4, -45, 45)
            if abs(angulo_alvo_deg) < 20:
                correcao = np.clip(angulo_alvo_deg * 0.5, -20, 20)
            return correcao
        else:
            # Há espaço frontal mas lateral muito próximo - ajusta suavemente
            # Mas ainda permite continuar se há espaço frontal
            if d_e < 8 and d_d > 15:
                # Obstáculo muito próximo à esquerda, mas espaço à direita
                # Ajusta levemente à direita mas continua
                return np.clip(angulo_alvo_deg * 0.3 + 15, -45, 45)
            elif d_d < 8 and d_e > 15:
                # Obstáculo muito próximo à direita, mas espaço à esquerda
                # Ajusta levemente à esquerda mas continua
                return np.clip(angulo_alvo_deg * 0.3 - 15, -45, 45)
            else:
                # Ambos lados muito próximos - usa fuzzy
                pass  # Continua para lógica fuzzy
    
    # REGRA 3: Espaço frontal médio (10-20cm) - precisa de análise mais cuidadosa
    if d_f >= 10 and d_f <= 20:
        # Se alvo está à frente e há espaço suficiente, continua
        if abs(angulo_alvo_deg) < 30:
            # Alvo está à frente - pode continuar se há espaço
            if d_f > 15:
                return np.clip(angulo_alvo_deg * 0.3, -30, 30)
            # Se espaço frontal é 10-15cm, precisa desviar se lateral muito próximo
            if (d_e < 8 and d_d > d_e + 5) or (d_d < 8 and d_e > d_d + 5):
                # Um lado muito próximo, outro tem espaço - desvia para o lado com espaço
                if d_d > d_e:
                    return 30
                else:
                    return -30
    
    # REGRA 4: Usa lógica fuzzy para casos não cobertos acima
    # Limita valores
    d_f = np.clip(d_f, 0, 100)
    d_e = np.clip(d_e, 0, 100)
    d_d = np.clip(d_d, 0, 100)
    ang_alvo = np.clip(angulo_alvo_deg, -180, 180)
    
    # Define entradas
    simulador_fuzzy.input['dist_frontal'] = d_f
    simulador_fuzzy.input['dist_esquerda'] = d_e
    simulador_fuzzy.input['dist_direita'] = d_d
    simulador_fuzzy.input['angulo_alvo'] = ang_alvo
    
    # Computa
    try:
        simulador_fuzzy.compute()
        angulo_correcao_valor = simulador_fuzzy.output['angulo_correcao']
        angulo_correcao_valor = np.clip(angulo_correcao_valor, -90, 90)
        
        # Verificação final: se há obstáculo próximo à frente e fuzzy sugeriu quase reto
        # força desvio mínimo
        if d_f < 15 and abs(angulo_correcao_valor) < 15:
            if d_d > d_e:
                angulo_correcao_valor = max(angulo_correcao_valor, 25)
            else:
                angulo_correcao_valor = min(angulo_correcao_valor, -25)
        
    except Exception as e:
        # Fallback simples
        if d_f < 15:
            angulo_correcao_valor = 50 if d_d > d_e else -50
        else:
            angulo_correcao_valor = np.clip(ang_alvo * 0.4, -40, 40)
    
    return angulo_correcao_valor

# ==============================================================
# INTERFACE GRÁFICA
# ==============================================================

def inicializar_interface():
    """Inicializa a interface gráfica"""
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 10))
    
    ax.set_xlim(0, MAP_SIZE)
    ax.set_ylim(0, MAP_SIZE)
    ax.set_title('Navegação Fuzzy - Robô até Alvo', fontsize=14)
    ax.set_xlabel('X (m)')
    ax.set_ylim(0, MAP_SIZE)
    ax.set_ylabel('Y (m)')
    ax.grid(True, alpha=0.3)
    
    # Elementos gráficos
    alvo, = ax.plot([], [], 'ro', markersize=12, label='Alvo', zorder=5)
    rob, = ax.plot([], [], 'bo', markersize=10, label='Robô', zorder=5)
    traj, = ax.plot([], [], 'b-', linewidth=1.5, alpha=0.6, label='Trajetória')
    ax.legend(loc='upper right')
    
    # Botão reiniciar
    ax_button = plt.axes([0.02, 0.02, 0.15, 0.04])
    button_reiniciar = widgets.Button(ax_button, 'Reiniciar', color='lightblue', hovercolor='lightgreen')
    reiniciar_simulacao = [False]
    
    def on_reiniciar_clicked(event):
        reiniciar_simulacao[0] = True
        print("\nReiniciando simulação...")
    
    button_reiniciar.on_clicked(on_reiniciar_clicked)
    
    return fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao

# ==============================================================
# SIMULAÇÃO
# ==============================================================

def simular(fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao):
    """Simulação principal do robô navegando até o alvo"""
    global OBSTACULOS, simulador_fuzzy
    
    # Reseta
    reiniciar_simulacao[0] = False
    simulador_fuzzy = None  # Reseta sistema fuzzy
    
    # Gera obstáculos
    OBSTACULOS = gerar_obstaculos_aleatorios()
    
    # Limpa e redesenha
    ax.clear()
    ax.set_xlim(0, MAP_SIZE)
    ax.set_ylim(0, MAP_SIZE)
    ax.set_title('Navegação Fuzzy - Robô até Alvo', fontsize=14)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.grid(True, alpha=0.3)
    
    # Desenha obstáculos
    for obs in OBSTACULOS:
        ax.add_patch(plt.Rectangle((obs[0], obs[2]), 
                                   obs[1] - obs[0], 
                                   obs[3] - obs[2],
                                   facecolor='gray', edgecolor='black', linewidth=1.5))
    
    # Recria elementos
    alvo, = ax.plot([], [], 'ro', markersize=12, label='Alvo', zorder=5)
    rob, = ax.plot([], [], 'bo', markersize=10, label='Robô', zorder=5)
    traj, = ax.plot([], [], 'b-', linewidth=1.5, alpha=0.6, label='Trajetória')
    ax.legend(loc='upper right')
    
    # Posição inicial
    x = 0.5
    y = 0.5
    theta = random.uniform(0, np.pi/2)
    
    # Posição do alvo
    tentativas_alvo = 0
    while True:
        alvo_x = random.uniform(1.0, MAP_SIZE - 1.0)
        alvo_y = random.uniform(1.0, MAP_SIZE - 1.0)
        dist_inicial = np.hypot(alvo_x - x, alvo_y - y)
        
        muito_proximo_obstaculo = False
        for obs in OBSTACULOS[4:]:
            centro_obs_x = (obs[0] + obs[1]) / 2
            centro_obs_y = (obs[2] + obs[3]) / 2
            dist_obs = np.hypot(alvo_x - centro_obs_x, alvo_y - centro_obs_y)
            if dist_obs < 0.8:
                muito_proximo_obstaculo = True
                break
        
        if not colide(alvo_x, alvo_y) and dist_inicial > 3.5 and not muito_proximo_obstaculo:
            break
        tentativas_alvo += 1
        if tentativas_alvo > 200:
            alvo_x = MAP_SIZE - 1.0
            alvo_y = MAP_SIZE - 1.0
            break
    
    # Atualiza visualização inicial
    alvo.set_data([alvo_x], [alvo_y])
    trajetoria_x = [x]
    trajetoria_y = [y]
    traj.set_data(trajetoria_x, trajetoria_y)
    rob.set_data([x], [y])
    plt.draw()
    plt.pause(0.1)
    
    print("=" * 60)
    print("NAVEGAÇÃO FUZZY - ROBÔ ATÉ ALVO")
    print("=" * 60)
    print(f"Posição inicial: ({x:.2f}, {y:.2f})")
    print(f"Posição do alvo: ({alvo_x:.2f}, {alvo_y:.2f})")
    print(f"Distância inicial: {np.hypot(alvo_x - x, alvo_y - y):.2f}m")
    print("=" * 60)
    print()
    
    # Loop principal
    max_steps = 5000
    distancia_minima = 0.08
    alvo_atingido = False
    
    # Variáveis para detecção de travamento
    historico_posicoes = []
    stuck_counter = 0
    last_x, last_y = x, y
    last_dist_alvo = np.hypot(alvo_x - x, alvo_y - y)
    
    for step in range(max_steps):
        if reiniciar_simulacao[0]:
            print("Reiniciando simulação...")
            break
        
        # ==========================================
        # LEITURA DE SENSORES
        # ==========================================
        sensores = {
            'frontal': raycast(x, y, theta),
            'esquerda': raycast(x, y, theta + np.pi/2),
            'direita': raycast(x, y, theta - np.pi/2)
        }
        
        dist_frontal = sensores['frontal']
        
        # Detecta se está cercado
        cercado = (sensores['frontal'] < 5 and sensores['esquerda'] < 5 and 
                  sensores['direita'] < 5)
        
        # ==========================================
        # CÁLCULO DE INFORMAÇÕES SOBRE O ALVO
        # ==========================================
        dx_alvo = alvo_x - x
        dy_alvo = alvo_y - y
        dist_alvo = np.hypot(dx_alvo, dy_alvo)
        
        # Ângulo do alvo em relação à direção atual
        angulo_absoluto_alvo = np.arctan2(dy_alvo, dx_alvo)
        angulo_relativo_alvo = angulo_absoluto_alvo - theta
        
        # Normaliza para [-pi, pi]
        while angulo_relativo_alvo > np.pi:
            angulo_relativo_alvo -= 2 * np.pi
        while angulo_relativo_alvo < -np.pi:
            angulo_relativo_alvo += 2 * np.pi
        
        angulo_relativo_alvo_deg = np.rad2deg(angulo_relativo_alvo)
        
        # ==========================================
        # CONTROLE FUZZY EFICIENTE (EFLC)
        # ==========================================
        # Passa também a direção atual para análise inteligente
        angulo_correcao = controlador_fuzzy_eflc(sensores, angulo_relativo_alvo_deg, theta)
        
        # Aplica correção
        theta += np.deg2rad(angulo_correcao)
        
        # ==========================================
        # MOVIMENTO
        # ==========================================
        novo_x = x + VELOCIDADE * np.cos(theta) * DT
        novo_y = y + VELOCIDADE * np.sin(theta) * DT
        
        # Verifica colisão
        if colide(novo_x, novo_y):
            # Encontra melhor direção
            melhor_angulo = None
            melhor_dist = 0
            
            for tentativa in range(16):
                ang_teste = theta + np.deg2rad(22.5 * tentativa)
                dist_teste = raycast(x, y, ang_teste)
                if dist_teste > melhor_dist:
                    melhor_dist = dist_teste
                    melhor_angulo = ang_teste
            
            if melhor_angulo is not None and melhor_dist > 1:
                theta = melhor_angulo
                novo_x = x + VELOCIDADE * np.cos(theta) * DT
                novo_y = y + VELOCIDADE * np.sin(theta) * DT
                
                if colide(novo_x, novo_y):
                    novo_x = x + VELOCIDADE * 0.5 * np.cos(theta) * DT
                    novo_y = y + VELOCIDADE * 0.5 * np.sin(theta) * DT
                    
        # Move
        if not colide(novo_x, novo_y):
            x, y = novo_x, novo_y
            trajetoria_x.append(x)
            trajetoria_y.append(y)
        else:
            # Último recurso: movimento mínimo
            movimento_feito = False
            for ang_ultimo in range(0, 360, 10):
                ang_rad = np.deg2rad(ang_ultimo)
                x_ultimo = x + VELOCIDADE * 0.2 * np.cos(ang_rad) * DT
                y_ultimo = y + VELOCIDADE * 0.2 * np.sin(ang_rad) * DT
                if not colide(x_ultimo, y_ultimo):
                    x, y = x_ultimo, y_ultimo
                    theta = ang_rad
                    trajetoria_x.append(x)
                    trajetoria_y.append(y)
                    movimento_feito = True
                    break
        
        # ==========================================
        # DETECÇÃO DE TRAVAMENTO
        # ==========================================
        movimento = np.hypot(x - last_x, y - last_y)
        progresso_alvo = last_dist_alvo - dist_alvo
        
        # Atualiza histórico
        historico_posicoes.append((x, y))
        if len(historico_posicoes) > 30:
            historico_posicoes.pop(0)
        
        # Detecta travamento
        if movimento < 0.001:
            stuck_counter += 3
        elif movimento < 0.003:
            stuck_counter += 1
        elif progresso_alvo < -0.03:
            stuck_counter += 2
        elif abs(progresso_alvo) < 0.005 and movimento < 0.015:
            stuck_counter += 1
        elif cercado:
            stuck_counter += 2
        else:
            stuck_counter = max(0, stuck_counter - 2)
        
        # Detecta loop
        em_loop = False
        if len(historico_posicoes) > 20:
            posicoes_proximas = 0
            for px, py in historico_posicoes[-25:]:
                if np.hypot(x - px, y - py) < 0.3:
                    posicoes_proximas += 1
            em_loop = posicoes_proximas > 12
        
        # Mecanismo de escape
        if stuck_counter > 10 or (em_loop and stuck_counter > 5) or cercado:
            if stuck_counter > 18 or em_loop:
                # Força ir em direção ao alvo
                angulo_direto_alvo = np.arctan2(dy_alvo, dx_alvo)
                diff_ang = angulo_direto_alvo - theta
                while diff_ang > np.pi:
                    diff_ang -= 2 * np.pi
                while diff_ang < -np.pi:
                    diff_ang += 2 * np.pi
                theta += diff_ang * 0.8
                stuck_counter = 0
            elif cercado:
                # Encontra direção com mais espaço
                melhor_angulo = None
                melhor_dist = 0
                for tentativa in range(16):
                    ang_teste = theta + np.deg2rad(22.5 * tentativa)
                    dist_teste = raycast(x, y, ang_teste)
                    if dist_teste > melhor_dist:
                        melhor_dist = dist_teste
                        melhor_angulo = ang_teste
                if melhor_angulo is not None:
                    theta = melhor_angulo
                    stuck_counter = max(0, stuck_counter - 5)
        
        # Atualiza variáveis
        last_x, last_y = x, y
        last_dist_alvo = dist_alvo
        
        # ==========================================
        # VERIFICA SE ALCANÇOU O ALVO
        # ==========================================
        if dist_alvo < distancia_minima and not alvo_atingido:
            alvo_atingido = True
            alvo.set_data([], [])
            traj.set_data(trajetoria_x, trajetoria_y)
            rob.set_data([x], [y])
            plt.pause(0.1)
            
            print(f"\n{'='*60}")
            print(f"ALVO ALCANÇADO!")
            print(f"Step: {step}")
            print(f"Distância final: {dist_alvo:.3f}m")
            print(f"{'='*60}")
            break
        
        # ==========================================
        # VISUALIZAÇÃO
        # ==========================================
        if step % 5 == 0:
            traj.set_data(trajetoria_x, trajetoria_y)
            rob.set_data([x], [y])
            plt.pause(0.01)
        
        # ==========================================
        # ESTATÍSTICAS
        # ==========================================
        if step % 200 == 0 and step > 0:
            print(f"Step {step:4d} | Pos: ({x:.2f}, {y:.2f}) | "
                  f"Dist alvo: {dist_alvo:.2f}m | "
                  f"Ângulo alvo: {angulo_relativo_alvo_deg:6.1f}° | "
                  f"Mov: {movimento:.4f}m | Stuck: {stuck_counter} | "
                  f"Progresso: {progresso_alvo:+.4f}m")
    
    # Estatísticas finais
    dist_final = np.hypot(alvo_x - x, alvo_y - y)
    print(f"\n{'='*60}")
    print(f"SIMULAÇÃO FINALIZADA")
    print(f"Distância final ao alvo: {dist_final:.3f}m")
    print(f"Total de passos: {step}")
    if dist_final < distancia_minima or alvo_atingido:
        print("STATUS: SUCESSO - Alvo alcançado!")
    else:
        print("STATUS: Nao alcancou o alvo")
    print(f"{'='*60}")
    print("Clique no botao 'Reiniciar' na tela para executar novamente")
    print("   ou feche a janela para encerrar o programa.")
    
    # Atualiza visualização final
    traj.set_data(trajetoria_x, trajetoria_y)
    rob.set_data([x], [y])
    plt.draw()
    
    # Aguarda reinício
    while not reiniciar_simulacao[0]:
        if not plt.get_fignums():
            return None
        plt.pause(0.1)
    
    return True

# ==============================================================
# EXECUÇÃO
# ==============================================================

if __name__ == "__main__":
    print("="*60)
    print("NAVEGAÇÃO FUZZY - ROBÔ ATÉ ALVO")
    print("="*60)
    print("Use o botao 'Reiniciar' na tela para executar novamente")
    print("   ou feche a janela para encerrar o programa.")
    print("="*60 + "\n")
    
    # Inicializa interface
    fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao = inicializar_interface()
    plt.show(block=False)
    
    while True:
        print("\n" + "="*60)
        print("INICIANDO NOVA SIMULAÇÃO...")
        print("="*60 + "\n")
        
        resultado = simular(fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao)
        
        if resultado is None:
            print("\nEncerrando programa. Obrigado por usar!")
            break
        
        if resultado:
            print("\n" + "="*60)
            print("PREPARANDO NOVA SIMULAÇÃO...")
            print("="*60 + "\n")
            continue
