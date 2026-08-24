const API_BASE_URL = "/api";


export async function getCurrentVessels() {
  const response = await fetch(
    `${API_BASE_URL}/vessels/`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje plovila (${response.status})`,
    );
  }

  return response.json();
}


export async function getVesselHistory(
  mmsi,
  limit = 500,
) {
  const response = await fetch(
    `${API_BASE_URL}/vessels/${encodeURIComponent(mmsi)}/history?limit=${limit}`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje povijesti plovila (${response.status})`,
    );
  }

  return response.json();
}


export async function getCurrentTraffic() {
  const response = await fetch(
    `${API_BASE_URL}/traffic/current`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje podataka o prometu (${response.status})`,
    );
  }

  return response.json();
}


export async function getPredictionStatus() {
  const response = await fetch(
    `${API_BASE_URL}/prediction/live/status`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje statusa predikcije (${response.status})`,
    );
  }

  return response.json();
}

export async function getLivePrediction() {
  const response = await fetch(
    `${API_BASE_URL}/prediction/live`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje live predikcije (${response.status})`,
    );
  }

  return response.json();
}


export async function getLiveAnalytics(
  hours = 24,
) {
  const response = await fetch(
    `${API_BASE_URL}/analytics/live?hours=${encodeURIComponent(hours)}`,
  );

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje analitike (${response.status})`,
    );
  }

  return response.json();
}