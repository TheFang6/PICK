import { api } from "./api";

export interface UserInfo {
  user_id: string;
  name: string;
}

export async function getMe(): Promise<UserInfo> {
  const res = await api.get("/me");
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

export async function logout(): Promise<void> {
  await api.post("/logout");
}
