/*
    Intended shape of the API response from the backend.
    Because the result is generic, the user must specify the type of the result when using this interface.
*/
export interface ApiResponse<T> {
    success: boolean,
    result: T
}