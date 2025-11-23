import numpy as np
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import random
import skfuzzy as fuzz
from skfuzzy import control as ctrl

MAP_SIZE = 6.0
ROBOT_RADIUS = 0.25
MARGEM_COLISAO = 0.001
VELOCIDADE = 0.3
DT = 0.1

def gerar_obstaculos_aleatorios():
    obstaculos = [
        [0, MAP_SIZE, 0, 0.25],
        [0, MAP_SIZE, MAP_SIZE-0.25, MAP_SIZE],
        [0, 0.25, 0, MAP_SIZE],
        [MAP_SIZE-0.25, MAP_SIZE, 0, MAP_SIZE],
    ]
    
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
        
        dist_inicial = np.hypot((x_min + x_max)/2 - 0.5, (y_min + y_max)/2 - 0.5)
        if dist_inicial < 1.0:
            tentativas += 1
            continue
        
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

def colide(x, y):
    margem = MARGEM_COLISAO
    for obs in OBSTACULOS:
        if (obs[0] - margem) <= x <= (obs[1] + margem) and \
           (obs[2] - margem) <= y <= (obs[3] + margem):
            return True
    return False

def raycast(x, y, angulo):
    dist = 0.0
    passo = 0.02
    
    while dist < MAP_SIZE:
        px = x + dist * np.cos(angulo)
        py = y + dist * np.sin(angulo)
        
        margem = MARGEM_COLISAO
        colidiu = False
        for obs in OBSTACULOS:
            if (obs[0] - margem) <= px <= (obs[1] + margem) and \
               (obs[2] - margem) <= py <= (obs[3] + margem):
                colidiu = True
                break
        
        if colidiu:
            return dist * 100
        
        dist += passo
    
    return 100.0

dist_frontal_universe = np.arange(0, 101, 1)
dist_lateral_universe = np.arange(0, 101, 1)
angulo_alvo_universe = np.arange(-180, 181, 1)
angulo_saida_universe = np.arange(-90, 91, 1)

dist_frontal = ctrl.Antecedent(dist_frontal_universe, 'dist_frontal')
dist_esquerda = ctrl.Antecedent(dist_lateral_universe, 'dist_esquerda')
dist_direita = ctrl.Antecedent(dist_lateral_universe, 'dist_direita')
angulo_alvo = ctrl.Antecedent(angulo_alvo_universe, 'angulo_alvo')

angulo_correcao = ctrl.Consequent(angulo_saida_universe, 'angulo_correcao', 
                                  defuzzify_method='centroid')

dist_frontal['muito_perto'] = fuzz.trapmf(dist_frontal_universe, [0, 0, 15, 25])
dist_frontal['perto'] = fuzz.trimf(dist_frontal_universe, [15, 35, 55])
dist_frontal['medio'] = fuzz.trimf(dist_frontal_universe, [40, 60, 80])
dist_frontal['longe'] = fuzz.trapmf(dist_frontal_universe, [60, 80, 100, 100])

for var in [dist_esquerda, dist_direita]:
    var['muito_perto'] = fuzz.trapmf(dist_lateral_universe, [0, 0, 10, 20])
    var['perto'] = fuzz.trimf(dist_lateral_universe, [10, 30, 50])
    var['medio'] = fuzz.trimf(dist_lateral_universe, [35, 55, 75])
    var['longe'] = fuzz.trapmf(dist_lateral_universe, [60, 80, 100, 100])

angulo_alvo['esquerda_forte'] = fuzz.trapmf(angulo_alvo_universe, [-180, -180, -90, -45])
angulo_alvo['esquerda'] = fuzz.trimf(angulo_alvo_universe, [-90, -45, 0])
angulo_alvo['frente'] = fuzz.trimf(angulo_alvo_universe, [-30, 0, 30])
angulo_alvo['direita'] = fuzz.trimf(angulo_alvo_universe, [0, 45, 90])
angulo_alvo['direita_forte'] = fuzz.trapmf(angulo_alvo_universe, [45, 90, 180, 180])

angulo_correcao['esquerda_forte'] = fuzz.trimf(angulo_saida_universe, [-90, -90, -50])
angulo_correcao['esquerda'] = fuzz.trimf(angulo_saida_universe, [-60, -35, -5])
angulo_correcao['esquerda_suave'] = fuzz.trimf(angulo_saida_universe, [-25, -12, 0])
angulo_correcao['reto'] = fuzz.trimf(angulo_saida_universe, [-10, 0, 10])
angulo_correcao['direita_suave'] = fuzz.trimf(angulo_saida_universe, [0, 12, 25])
angulo_correcao['direita'] = fuzz.trimf(angulo_saida_universe, [5, 35, 60])
angulo_correcao['direita_forte'] = fuzz.trimf(angulo_saida_universe, [50, 90, 90])

def inicializar_sistema_fuzzy():
    regras = []
    
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & dist_esquerda['longe'], angulo_correcao['esquerda_forte']))
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & dist_direita['longe'], angulo_correcao['direita_forte']))
    
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & dist_esquerda['muito_perto'], angulo_correcao['direita_forte']))
    regras.append(ctrl.Rule(dist_frontal['muito_perto'] & dist_direita['muito_perto'], angulo_correcao['esquerda_forte']))
    
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_esquerda['medio'], angulo_correcao['direita_suave']))
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_direita['medio'], angulo_correcao['esquerda_suave']))
    
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_esquerda['perto'], angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['perto'] & dist_direita['perto'], angulo_correcao['esquerda']))

    regras.append(ctrl.Rule(dist_esquerda['perto'] & dist_frontal['medio'], angulo_correcao['direita_suave']))
    regras.append(ctrl.Rule(dist_direita['perto'] & dist_frontal['medio'], angulo_correcao['esquerda_suave']))
    
    regras.append(ctrl.Rule(dist_frontal['perto'] & angulo_alvo['frente'] & dist_esquerda['longe'], 
                            angulo_correcao['esquerda'])) 
    regras.append(ctrl.Rule(dist_frontal['perto'] & angulo_alvo['frente'] & dist_direita['longe'], 
                            angulo_correcao['direita']))

    regras.append(ctrl.Rule(dist_frontal['longe'], angulo_correcao['reto']))
    
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['esquerda'], angulo_correcao['esquerda']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['direita'], angulo_correcao['direita']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['esquerda_forte'], angulo_correcao['esquerda_forte']))
    regras.append(ctrl.Rule(dist_frontal['longe'] & angulo_alvo['direita_forte'], angulo_correcao['direita_forte']))
    
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['frente'], angulo_correcao['reto']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['esquerda'], angulo_correcao['esquerda_suave']))
    regras.append(ctrl.Rule(dist_frontal['medio'] & angulo_alvo['direita'], angulo_correcao['direita_suave']))

    sistema_fuzzy = ctrl.ControlSystem(regras)
    return ctrl.ControlSystemSimulation(sistema_fuzzy)

simulador_fuzzy = None

def controlador_fuzzy_puro(sensores, angulo_alvo_deg):
    global simulador_fuzzy
    if simulador_fuzzy is None:
        simulador_fuzzy = inicializar_sistema_fuzzy()
    
    d_f = np.clip(sensores['frontal'], 0, 100)
    d_e = np.clip(sensores['esquerda'], 0, 100)
    d_d = np.clip(sensores['direita'], 0, 100)
    ang_alvo = np.clip(angulo_alvo_deg, -180, 180)
    
    simulador_fuzzy.input['dist_frontal'] = d_f
    simulador_fuzzy.input['dist_esquerda'] = d_e
    simulador_fuzzy.input['dist_direita'] = d_d
    simulador_fuzzy.input['angulo_alvo'] = ang_alvo
    
    try:
        simulador_fuzzy.compute()
        output = simulador_fuzzy.output['angulo_correcao']
        
        if d_f < 12 and abs(output) < 15:
             return 60 if d_e < d_d else -60
             
        return output
    except Exception as e:
        if d_f < 30:
            return 45 if d_e < d_d else -45
        else:
            return np.clip(ang_alvo, -45, 45)

def inicializar_interface():
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, MAP_SIZE)
    ax.set_ylim(0, MAP_SIZE)
    ax.set_title('Navegação Fuzzy', fontsize=14)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.grid(True, alpha=0.3)
    
    alvo, = ax.plot([], [], 'ro', markersize=12, label='Alvo', zorder=5)
    rob, = ax.plot([], [], 'bo', markersize=10, label='Robô', zorder=5)
    traj, = ax.plot([], [], 'b-', linewidth=1.5, alpha=0.6, label='Trajetória')
    ax.legend(loc='upper right')
    
    ax_button = plt.axes([0.02, 0.02, 0.15, 0.04])
    button_reiniciar = widgets.Button(ax_button, 'Reiniciar', color='lightblue', hovercolor='lightgreen')
    reiniciar_simulacao = [False]
    
    def on_reiniciar_clicked(event):
        reiniciar_simulacao[0] = True
    
    button_reiniciar.on_clicked(on_reiniciar_clicked)
    return fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao

def simular(fig, ax, alvo, rob, traj, button_reiniciar, reiniciar_simulacao):
    global OBSTACULOS, simulador_fuzzy
    
    reiniciar_simulacao[0] = False
    simulador_fuzzy = None
    OBSTACULOS = gerar_obstaculos_aleatorios()
    
    ax.clear()
    ax.set_xlim(0, MAP_SIZE)
    ax.set_ylim(0, MAP_SIZE)
    ax.set_title('Navegação Fuzzy', fontsize=14)
    ax.grid(True, alpha=0.3)
    
    for obs in OBSTACULOS:
        ax.add_patch(plt.Rectangle((obs[0], obs[2]), obs[1]-obs[0], obs[3]-obs[2], color='gray'))
    
    alvo, = ax.plot([], [], 'ro', markersize=12)
    rob, = ax.plot([], [], 'bo', markersize=10)
    traj, = ax.plot([], [], 'b-', linewidth=1.5, alpha=0.6)
    
    x, y = 0.5, 0.5
    theta = random.uniform(0, np.pi/2)
    
    correcao_anterior = 0 
    
    while True:
        alvo_x, alvo_y = random.uniform(1, MAP_SIZE-1), random.uniform(1, MAP_SIZE-1)
        if not colide(alvo_x, alvo_y) and np.hypot(alvo_x-x, alvo_y-y) > 3.0:
            break
            
    alvo.set_data([alvo_x], [alvo_y])
    trajetoria_x, trajetoria_y = [x], [y]
    print(f"Iniciando: Alvo em ({alvo_x:.1f}, {alvo_y:.1f})")
    
    stuck_counter = 0
    last_pos = (x, y)
    
    for step in range(3000):
        if reiniciar_simulacao[0]: break
        
        sensores = {
            'frontal': raycast(x, y, theta),
            'esquerda': raycast(x, y, theta + np.pi/2),
            'direita': raycast(x, y, theta - np.pi/2)
        }
        
        dx, dy = alvo_x - x, alvo_y - y
        dist_alvo = np.hypot(dx, dy)
        ang_abs_alvo = np.arctan2(dy, dx)
        ang_rel_alvo = ang_abs_alvo - theta
        
        while ang_rel_alvo > np.pi: ang_rel_alvo -= 2*np.pi
        while ang_rel_alvo < -np.pi: ang_rel_alvo += 2*np.pi
        ang_deg = np.rad2deg(ang_rel_alvo)
        
        correcao_alvo = controlador_fuzzy_puro(sensores, ang_deg)
        
        if sensores['frontal'] < 25 or sensores['esquerda'] < 15 or sensores['direita'] < 15:
            fator_inercia = 0.0
        else:
            fator_inercia = 0.4
            
        correcao_efetiva = ((1.0 - fator_inercia) * correcao_alvo) + (fator_inercia * correcao_anterior)
        correcao_anterior = correcao_efetiva
        
        theta += np.deg2rad(correcao_efetiva)
        novo_x = x + VELOCIDADE * np.cos(theta) * DT
        novo_y = y + VELOCIDADE * np.sin(theta) * DT
        
        if not colide(novo_x, novo_y):
            x, y = novo_x, novo_y
            trajetoria_x.append(x)
            trajetoria_y.append(y)
        else:
            theta += np.pi/2 
        
        if step % 20 == 0:
            dist_moved = np.hypot(x - last_pos[0], y - last_pos[1])
            if dist_moved < 0.2: 
                stuck_counter += 1
            else: 
                stuck_counter = 0
            last_pos = (x, y)
            
        if stuck_counter > 3:
            print("Robô travado! Executando manobra de escape...")
            theta += random.choice([-1, 1]) * (np.pi/2)
            correcao_anterior = 0 
            stuck_counter = 0 
            
        if dist_alvo < 0.05:
            print("ALVO ALCANÇADO!")
            break
            
        if step % 5 == 0:
            rob.set_data([x], [y])
            traj.set_data(trajetoria_x, trajetoria_y)
            plt.pause(0.001)
            
    print("Fim da simulação.")
    while not reiniciar_simulacao[0]:
        if not plt.get_fignums(): return None
        plt.pause(0.1)
    return True

if __name__ == "__main__":
    fig, ax, alvo, rob, traj, btn, reiniciar = inicializar_interface()
    plt.show(block=False)
    while True:
        if simular(fig, ax, alvo, rob, traj, btn, reiniciar) is None: break