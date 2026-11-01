/* Entrega 4. Sem credenciais nem URLs de Traccar no navegador. */
(() => {
  'use strict';
  const raiz = document.getElementById('gps-monitoramento');
  if (!raiz) return;
  const alerta = document.getElementById('gps-alerta');
  const status = document.getElementById('gps-atualizacao');
  const lista = document.getElementById('gps-lista');
  const numeros = {
    total: document.getElementById('gps-total'),
    recentes: document.getElementById('gps-recentes'),
    antigos: document.getElementById('gps-antigos'),
    semPosicao: document.getElementById('gps-sem-posicao'),
  };
  const nomesEstado = {
    recente: 'Posição recente',
    atrasada: 'Posição atrasada',
    desatualizada: 'Posição desatualizada',
    sem_horario: 'Horário indisponível',
    sem_posicao: 'Sem posição GPS',
  };
  const estadoValido = (s) => Object.prototype.hasOwnProperty.call(nomesEstado, s) ? s : 'sem_posicao';
  const hora = (v) => {
    if (!v) return 'Não informada';
    const dt = new Date(v);
    return Number.isNaN(dt.getTime()) ? 'Horário inválido' : dt.toLocaleString('pt-BR');
  };
  const formatar = (v, unidade) => typeof v === 'number' && Number.isFinite(v)
    ? `${v.toLocaleString('pt-BR')} ${unidade}` : 'Não informado';

  if (!window.L) {
    status.textContent = 'Não foi possível carregar a biblioteca de mapas.';
    alerta.hidden = false;
    alerta.textContent = 'O mapa não está disponível. Verifique o carregamento do Leaflet.';
    return;
  }

  const mapa = L.map('gps-mapa').setView([-7.67, -36.88], 10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapa);
  const camada = L.layerGroup().addTo(mapa);
  let ajustarVisaoInicial = true;
  let carregando = false;

  function popupVeiculo(v) {
    // textContent previne injeção de HTML a partir de nomes externos do GPS.
    const caixa = document.createElement('div');
    const titulo = document.createElement('strong');
    titulo.textContent = `${v.placa} — ${v.modelo}`;
    caixa.appendChild(titulo);
    const linhas = [
      `GPS: ${v.gps_nome}`,
      `Localização: ${nomesEstado[estadoValido(v.estado_localizacao)]}`,
      `Última posição: ${hora(v.horario)}`,
      `Conexão Traccar: ${v.status_dispositivo || 'unknown'}`,
      `Velocidade: ${formatar(v.velocidade_kmh, 'km/h')}`,
      `Bateria: ${formatar(v.bateria, '%')}`,
    ];
    for (const texto of linhas) {
      const p = document.createElement('p');
      p.textContent = texto;
      p.style.margin = '4px 0';
      caixa.appendChild(p);
    }
    return caixa;
  }

  function mostrarDados(dados) {
    const resumo = dados.resumo || {};
    numeros.total.textContent = resumo.total_vinculados ?? 0;
    numeros.recentes.textContent = resumo.recentes ?? 0;
    numeros.antigos.textContent = (resumo.atrasadas || 0) + (resumo.desatualizadas || 0) + (resumo.sem_horario || 0);
    numeros.semPosicao.textContent = resumo.sem_posicao ?? 0;

    camada.clearLayers();
    lista.replaceChildren();
    const pontos = [];
    for (const veiculo of dados.veiculos || []) {
      const lat = veiculo.latitude;
      const lon = veiculo.longitude;
      const temPosicao = typeof lat === 'number' && typeof lon === 'number' &&
        Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
      let marcador = null;
      if (temPosicao) {
        const estado = estadoValido(veiculo.estado_localizacao);
        const cores = { recente: '#169968', atrasada: '#d89b22', desatualizada: '#677487', sem_horario: '#d89b22', sem_posicao: '#677487' };
        marcador = L.circleMarker([lat, lon], {
          radius: 9, weight: 2, color: '#ffffff',
          fillColor: cores[estado], fillOpacity: 0.95,
        }).addTo(camada);
        marcador.bindPopup(popupVeiculo(veiculo));
        pontos.push([lat, lon]);
      }
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'gps-item';
      botao.disabled = !temPosicao;
      const titulo = document.createElement('span');
      titulo.className = 'gps-item-titulo';
      titulo.textContent = `${veiculo.placa} — ${veiculo.modelo}`;
      const subtitulo = document.createElement('span');
      subtitulo.className = 'gps-item-sub';
      subtitulo.textContent = `GPS: ${veiculo.gps_nome} · Última: ${hora(veiculo.horario)}`;
      const estado = estadoValido(veiculo.estado_localizacao);
      const badge = document.createElement('span');
      badge.className = `gps-badge gps-badge-${estado}`;
      badge.textContent = nomesEstado[estado];
      botao.append(titulo, subtitulo, badge);
      if (marcador) {
        botao.addEventListener('click', () => {
          mapa.setView(marcador.getLatLng(), Math.max(mapa.getZoom(), 13));
          marcador.openPopup();
        });
      }
      lista.appendChild(botao);
    }
    if (!(dados.veiculos || []).length) {
      const vazio = document.createElement('p');
      vazio.className = 'text-sm text-gray-500';
      vazio.textContent = 'Nenhum veículo vinculado a um GPS administrativamente ativo.';
      lista.appendChild(vazio);
    }
    if (ajustarVisaoInicial && pontos.length) {
      mapa.fitBounds(L.latLngBounds(pontos).pad(0.2), { maxZoom: 15 });
      ajustarVisaoInicial = false;
    }
    status.textContent = `Consulta realizada: ${hora(dados.consultado_em)} · Atualização a cada 60 segundos`;
  }

  async function atualizarMapa() {
    if (carregando) return;
    carregando = true;
    try {
      const resposta = await fetch(raiz.dataset.url, {
        cache: 'no-store', credentials: 'same-origin', headers: { 'Accept': 'application/json' },
      });
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();
      if (!Array.isArray(dados.veiculos) || !dados.resumo) throw new Error('Resposta inesperada');
      mostrarDados(dados);
      alerta.hidden = true;
      alerta.textContent = '';
    } catch (e) {
      // Mantém os últimos marcadores com aviso claro de dados desatualizados.
      alerta.hidden = false;
      alerta.textContent = 'Não foi possível atualizar o Traccar. Os marcadores, se existirem, mostram dados da última consulta bem-sucedida.';
      status.textContent = 'Falha na atualização — dados potencialmente desatualizados.';
    } finally {
      carregando = false;
    }
  }

  atualizarMapa();
  const intervalo = Number(raiz.dataset.intervalo) || 60000;
  window.setInterval(atualizarMapa, intervalo);
})();
