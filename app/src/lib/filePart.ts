import { File } from "expo-file-system";

// Phone: Expo's fetch only uploads FormData parts that are Blobs or expose bytes(), not React Native's
// { uri, name, type } objects ("Unsupported FormDataPart implementation"). expo-file-system's File does.
export function filePart(uri: string): Blob {
  return new File(uri) as unknown as Blob;
}
