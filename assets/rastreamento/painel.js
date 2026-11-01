/* Entrega 6: resumo GPS no painel, reaproveitando a API de monitoramento.
 * Dados de veículos e dispositivos não são interpolados em innerHTML. */
(() => {
  'use strict';
  const raiz = document.getElementById('painel-gps-widget');
  if (!raiz) return;
  const alerta = document.getElementById('painel-gps-alerta');
  const status = document.getElementById('painel-gps-atualizacao');
  const lista = document.getElementById('painel-gps-lista');
  const listaInfo = document.getElementById('painel-gps-lista-info');
  const numeros = {
    total: document.getElementById('painel-gps-total'),
    recentes: document.getElementById('painel-gps-recentes'),
    antigos: document.getElementById('painel-gps-antigos'),
    semPosicao: document.getElementById('painel-gps-sem-posicao'),
  };
  const nomesEstado = {
    recente: 'Posição recente',
    atrasada: 'Posição atrasada',
    desatualizada: 'Posição desatualizada',
    sem_horario: 'Horário indisponível',
    sem_posicao: 'Sem posição GPS',
  };
  const cores = {
    recente: '#169968', atrasada: '#d89b22',
    desatualizada: '#677487', sem_horario: '#d89b22', sem_posicao: '#677487',
  };
  const estadoValido = (valor) => Object.hasOwn(nomesEstado, valor) ? valor : 'sem_posicao';
  const hora = (valor) => {
    if (!valor) return 'Não informada';
    const data = new Date(valor);
    return Number.isNaN(data.getTime()) ? 'Horário inválido' : data.toLocaleString('pt-BR');
  };
  const texto = (valor) => String(valor ?? 'Não informado');

  if (!window.L) {
    status.textContent = 'Mini mapa indisponível.';
    alerta.hidden = false;
    alerta.textContent = 'Não foi possível carregar o mapa. Verifique o carregamento do Leaflet.';
    return;
  }

  const mapa = L.map('painel-gps-mapa', { zoomControl: false }).setView([-7.67, -36.88], 10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapa);
  L.control.zoom({ position: 'topright' }).addTo(mapa);
  const camada = L.layerGroup().addTo(mapa);
  let ajustarVisao = true;
  let carregando = false;

  function popupVeiculo(veiculo, estado) {
    const caixa = document.createElement('div');
    const titulo = document.createElement('strong');
    titulo.textContent = `${texto(veiculo.placa)} — ${texto(veiculo.modelo)}`;
    caixa.appendChild(titulo);
    for (const linha of [
      `GPS: ${texto(veiculo.gps_nome)}`,
      `Localização: ${nomesEstado[estado]}`,
      `Última posição: ${hora(veiculo.horario)}`,
    ]) {
      const p = document.createElement('p');
      p.textContent = linha;
      p.style.margin = '4px 0';
      caixa.appendChild(p);
    }
    return caixa;
  }

  function criarItem(veiculo, estado, marcador) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'painel-gps-item';
    const topo = document.createElement('span');
    topo.className = 'painel-gps-item-topo';
    const titulo = document.createElement('strong');
    titulo.textContent = `${texto(veiculo.placa)} — ${texto(veiculo.modelo)}`;
    const badge = document.createElement('span');
    badge.className = `painel-gps-badge painel-gps-badge-${estado}`;
    badge.textContent = nomesEstado[estado];
    topo.append(titulo, badge);
    const dispositivo = document.createElement('span');
    dispositivo.className = 'painel-gps-item-detalhe';
    dispositivo.textContent = `GPS: ${texto(veiculo.gps_nome)}`;
    const horario = document.createElement('span');
    horario.className = 'painel-gps-item-detalhe';
    horario.textContent = `Última: ${hora(veiculo.horario)}`;
    item.append(topo, dispositivo, horario);
    if (marcador) {
      item.addEventListener('click', () => {
        mapa.setView(marcador.getLatLng(), Math.max(mapa.getZoom(), 13));
        marcador.openPopup();
      });
    } else {
      item.disabled = true;
    }
    return item;
  }

  function renderizar(dados) {
    const resumo = dados.resumo;
    numeros.total.textContent = resumo.total_vinculados ?? 0;
    numeros.recentes.textContent = resumo.recentes ?? 0;
    numeros.antigos.textContent = (resumo.atrasadas || 0) + (resumo.desatualizadas || 0) + (resumo.sem_horario || 0);
    numeros.semPosicao.textContent = resumo.sem_posicao ?? 0;

    camada.clearLayers();
    lista.replaceChildren();
    const pontos = [];
    const veiculos = dados.veiculos;
    for (const [indice, veiculo] of veiculos.entries()) {
      const estado = estadoValido(veiculo.estado_localizacao);
      const lat = veiculo.latitude;
      const lon = veiculo.longitude;
      const temPosicao = typeof lat === 'number' && typeof lon === 'number' &&
        Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
      let marcador = null;
      if (temPosicao) {
        marcador = L.circleMarker([lat, lon], {
          radius: 8, weight: 2, color: '#ffffff', fillColor: cores[estado], fillOpacity: 0.95,
        }).addTo(camada);
        marcador.bindPopup(popupVeiculo(veiculo, estado));
        pontos.push([lat, lon]);
      }
      // O mapa apresenta TODOS os pontos; a lista resume os cinco primeiros.
      if (indice < 5) lista.appendChild(criarItem(veiculo, estado, marcador));
    }
    if (!veiculos.length) {
      const vazio = document.createElement('p');
      vazio.className = 'text-sm text-gray-500';
      vazio.textContent = 'Nenhum veículo vinculado a GPS ativo.';
      lista.appendChild(vazio);
    }
    listaInfo.textContent = veiculos.length > 5
      ? `Exibindo 5 de ${veiculos.length} veículos na lista. Todos os pontos disponíveis aparecem no mapa.`
      : `${veiculos.length} veículo(s) monitorado(s).`;
    if (ajustarVisao && pontos.length) {
      mapa.fitBounds(L.latLngBounds(pontos).pad(0.25), { maxZoom: 13 });
      ajustarVisao = false;
    }
    status.textContent = `Consulta: ${hora(dados.consultado_em)} · a cada 60 segundos`;
  }

  async function atualizar() {
    if (carregando) return;
    carregando = true;
    try {
      const resposta = await fetch(raiz.dataset.url, {
        cache: 'no-store', credentials: 'same-origin', headers: { Accept: 'application/json' },
      });
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();
      if (!Array.isArray(dados.veiculos) || !dados.resumo || typeof dados.resumo !== 'object') {
        throw new Error('Resposta de monitoramento inválida');
      }
      renderizar(dados);
      alerta.hidden = true;
      alerta.textContent = '';
    } catch (erro) {
      alerta.hidden = false;
      alerta.textContent = 'Falha ao atualizar o GPS. Os marcadores e indicadores, se existirem, são da última consulta bem-sucedida.';
      status.textContent = 'Atualização indisponível — dados potencialmente antigos.';
    } finally {
      carregando = false;
    }
  }

  atualizar();
  window.setInterval(atualizar, Number(raiz.dataset.intervalo) || 60000);
})();
