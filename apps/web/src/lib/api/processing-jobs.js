const API_BASE_URL_ERROR = "Missing public API base URL.";

function getApiBaseUrl() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error(API_BASE_URL_ERROR);
  }
  return apiBaseUrl;
}

export class ProcessingJobRequestError extends Error {
  constructor(status, payload) {
    super("Processing job request failed.");
    this.name = "ProcessingJobRequestError";
    this.status = status;
    this.payload = payload;
  }
}

function buildHeaders(accessToken, organizationId) {
  if (!accessToken) {
    throw new Error("Missing Supabase access token.");
  }
  if (!organizationId) {
    throw new Error("Missing active organization.");
  }

  return {
    Authorization: `Bearer ${accessToken}`,
    "X-Organization-Id": organizationId,
  };
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ProcessingJobRequestError(response.status, payload);
  }
  return payload;
}

export async function fetchProcessingJob(
  { jobId, accessToken, organizationId },
  fetchImpl = fetch,
) {
  if (!jobId) {
    throw new Error("Missing processing job id.");
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/processing-jobs/${jobId}`, {
    method: "GET",
    headers: buildHeaders(accessToken, organizationId),
  });

  return parseResponse(response);
}

export async function fetchDocumentProcessingJobs(
  { documentId, accessToken, organizationId },
  fetchImpl = fetch,
) {
  if (!documentId) {
    throw new Error("Missing document id.");
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/documents/${documentId}/processing-jobs`, {
    method: "GET",
    headers: buildHeaders(accessToken, organizationId),
  });

  return parseResponse(response);
}
