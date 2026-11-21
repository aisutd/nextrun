// Web: uploads always carry a real Blob / File, so local uris never reach here.
export function filePart(uri: string): Blob {
  throw new Error(`Cannot upload a local file uri on the web: ${uri}`);
}
