const API_BASE_URL = '/api'

export async function getCurrentVessels() {
  const response = await fetch(
    `${API_BASE_URL}/vessels/?limit=500`,
  )

  if (!response.ok) {
    throw new Error(
      `Neuspješno dohvaćanje plovila (${response.status})`,
    )
  }

  return response.json()
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