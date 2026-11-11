(function () {
  const dados = window.dadosGraficos;
  if (!dados || typeof Chart === "undefined") {
    return;
  }

  const estiloBase = {
    font: { family: "ui-sans-serif, system-ui, sans-serif" },
    color: "#475569",
  };
  Chart.defaults.font = { ...Chart.defaults.font, ...estiloBase.font };
  Chart.defaults.color = estiloBase.color;

  const elementoStatus = document.getElementById("grafico-status");
  if (elementoStatus) {
    new Chart(elementoStatus, {
      type: "doughnut",
      data: {
        labels: dados.status.labels,
        datasets: [
          {
            data: dados.status.valores,
            backgroundColor: dados.status.cores,
            borderWidth: 2,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  const elementoCategorias = document.getElementById("grafico-categorias");
  if (elementoCategorias) {
    new Chart(elementoCategorias, {
      type: "bar",
      data: {
        labels: dados.categorias.labels,
        datasets: dados.categorias.series.map((serie) => ({
          label: serie.label,
          data: serie.valores,
          backgroundColor: serie.cor,
          borderRadius: 4,
        })),
      },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
        },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }
})();
