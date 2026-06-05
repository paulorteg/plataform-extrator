export const appRoutes = [
  {
    id: "dashboard",
    label: "Visao geral",
    path: "#/",
    description: "Resumo operacional do MVP.",
  },
  {
    id: "documents",
    label: "Documentos",
    path: "#/documents",
    description: "Entrada e acompanhamento documental.",
  },
  {
    id: "upload",
    label: "Upload de BO",
    path: "#/upload",
    description: "Envio seguro de documentos sinteticos ou anonimizados.",
  },
  {
    id: "occurrences",
    label: "Ocorrencias",
    path: "#/occurrences",
    description: "Lista e detalhe de ocorrencias extraidas.",
  },
  {
    id: "review",
    label: "Revisao",
    path: "#/review",
    description: "Revisao humana de campos e evidencias.",
  },
];

export function getCurrentRoute(hash) {
  const currentHash = hash ?? (typeof window !== "undefined" ? window.location.hash : "");

  return appRoutes.find((route) => route.path === currentHash) ?? appRoutes[0];
}
