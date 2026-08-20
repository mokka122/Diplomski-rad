const API_BASE_URL =
  "/api";


const GOOGLE_CLIENT_ID =
  import.meta.env
    .VITE_GOOGLE_CLIENT_ID;


let cachedUser =
  undefined;


export function getGoogleClientId() {
  if (!GOOGLE_CLIENT_ID) {
    throw new Error(
      "VITE_GOOGLE_CLIENT_ID is missing.",
    );
  }

  return GOOGLE_CLIENT_ID;
}


/* =========================================================
   GOOGLE IDENTITY SCRIPT
   ========================================================= */

export function loadGoogleIdentityScript() {
  return new Promise(
    (
      resolve,
      reject,
    ) => {
      if (
        window.google
          ?.accounts
          ?.id
      ) {
        resolve(
          window.google
        );

        return;
      }


      const existingScript =
        document.querySelector(
          'script[data-oceaneye-google-identity="true"]',
        );


      if (existingScript) {
        existingScript.addEventListener(
          "load",
          () =>
            resolve(
              window.google
            ),
          {
            once: true,
          },
        );

        existingScript.addEventListener(
          "error",
          () =>
            reject(
              new Error(
                "Unable to load Google Identity Services.",
              ),
            ),
          {
            once: true,
          },
        );

        return;
      }


      const script =
        document.createElement(
          "script"
        );

      script.src =
        "https://accounts.google.com/gsi/client";

      script.async = true;
      script.defer = true;

      script.dataset
        .oceaneyeGoogleIdentity =
        "true";


      script.onload = () => {
        resolve(
          window.google
        );
      };


      script.onerror = () => {
        reject(
          new Error(
            "Unable to load Google Identity Services.",
          ),
        );
      };


      document.head.appendChild(
        script
      );
    },
  );
}


/* =========================================================
   GOOGLE LOGIN
   ========================================================= */

export async function loginWithGoogle(
  credential,
) {
  const response =
    await fetch(
      `${API_BASE_URL}/auth/google`,
      {
        method: "POST",

        credentials:
          "include",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify({
            credential,
          }),
      },
    );


  if (!response.ok) {
    const data =
      await response
        .json()
        .catch(
          () => null
        );

    throw new Error(
      data?.detail ||
      `Google authentication failed (${response.status})`,
    );
  }


  const data =
    await response.json();


  cachedUser =
    data.user;


  return data.user;
}


/* =========================================================
   CURRENT USER
   ========================================================= */

export async function getCurrentUser(
  force = false,
) {
  if (
    !force &&
    cachedUser !== undefined
  ) {
    return cachedUser;
  }


  const response =
    await fetch(
      `${API_BASE_URL}/auth/me`,
      {
        credentials:
          "include",
      },
    );


  if (
    response.status === 401
  ) {
    cachedUser = null;

    return null;
  }


  if (!response.ok) {
    throw new Error(
      `Unable to verify session (${response.status})`,
    );
  }


  cachedUser =
    await response.json();


  return cachedUser;
}


/* =========================================================
   LOGOUT
   ========================================================= */

export async function logout() {
  await fetch(
    `${API_BASE_URL}/auth/logout`,
    {
      method:
        "POST",

      credentials:
        "include",
    },
  );


  cachedUser =
    null;
}