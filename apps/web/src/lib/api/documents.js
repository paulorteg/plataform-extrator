const API_BASE_URL_ERROR = "Missing public API base URL.";

function getApiBaseUrl() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error(API_BASE_URL_ERROR);
  }
  return apiBaseUrl;
}

export class DocumentUploadRequestError extends Error {
  constructor(status, payload) {
    super("Document upload failed.");
    this.name = "DocumentUploadRequestError";
    this.status = status;
    this.payload = payload;
  }
}

export async function uploadDocument({ file, accessToken, organizationId }, fetchImpl = fetch) {
  if (!file) {
    throw new Error("Missing upload file.");
  }
  if (!accessToken) {
    throw new Error("Missing Supabase access token.");
  }
  if (!organizationId) {
    throw new Error("Missing active organization.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchImpl(`${getApiBaseUrl()}/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "X-Organization-Id": organizationId,
    },
    body: formData,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new DocumentUploadRequestError(response.status, payload);
  }

  return payload;
}
