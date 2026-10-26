import apiAdmin from "./apiAdmin";

export const getSseToken = async () => {
  const response = await apiAdmin.post("/sse/token");
  return response.data.sse_token;
};
