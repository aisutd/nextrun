import { Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import * as SecureStore from "expo-secure-store";
import type { AppData } from "./types";
const key = "nextrun.v1";
const path = `${FileSystem.documentDirectory}nextrun-v1.json`;
export async function readData(): Promise<Partial<AppData> | null> {
  try {
    const raw =
      Platform.OS === "web"
        ? globalThis.localStorage?.getItem(key)
        : await FileSystem.readAsStringAsync(path);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
// Serialize writes so a slow earlier write can never replace a more recent state.
let writes = Promise.resolve();
export function persist(data: AppData): Promise<void> {
  const raw = JSON.stringify({
    ...data,
    account: Platform.OS === "web" ? data.account : null,
  });
  writes = writes
    .catch(() => {})
    .then(async () => {
      if (Platform.OS === "web") globalThis.localStorage?.setItem(key, raw);
      else {
        await FileSystem.writeAsStringAsync(path + ".tmp", raw);
        await FileSystem.moveAsync({ from: path + ".tmp", to: path });
        if (data.account)
          await SecureStore.setItemAsync(
            key + ".account",
            JSON.stringify(data.account),
          );
        else await SecureStore.deleteItemAsync(key + ".account");
      }
    });
  return writes;
}
export async function readAccount() {
  if (Platform.OS === "web") return null;
  try {
    const a = await SecureStore.getItemAsync(key + ".account");
    return a ? JSON.parse(a) : null;
  } catch {
    return null;
  }
}
export async function keepImage(uri: string) {
  if (Platform.OS === "web" || !FileSystem.documentDirectory) return uri;
  const to =
    FileSystem.documentDirectory +
    "photo-" +
    Date.now() +
    "." +
    (uri.split(".").pop()?.split("?")[0] || "jpg");
  await FileSystem.copyAsync({ from: uri, to });
  return to;
}
