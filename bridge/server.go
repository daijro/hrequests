package main

/*
#include <stdlib.h>
*/
import "C"

import (
	"fmt"
	"io"
	"net/url"
	"os"
	"sync"

	http "github.com/bogdanfinn/fhttp"
	tls_client_cffi "github.com/bogdanfinn/tls-client/cffi_src"
	json "github.com/goccy/go-json"
	"github.com/google/uuid"
)

/*
Offers a http server that can be used to make requests to tls-client
*/

type ResponseWrapper struct {
	// wrapper for multirequest return type
	IsHistory bool                        `json:"isHistory"`
	Response  *tls_client_cffi.Response   `json:"response,omitempty"`
	History   []*tls_client_cffi.Response `json:"history,omitempty"`
}

type IndexedResponseWrapper struct {
	int
	*ResponseWrapper
}

type ExtendedRequestInput struct {
	tls_client_cffi.RequestInput
	WantHistory bool `json:"wantHistory"`
}

func extractBody(w http.ResponseWriter, r *http.Request) []byte {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST method is allowed", http.StatusMethodNotAllowed)
		return nil
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return nil
	}
	defer r.Body.Close()

	return body
}

func requestHandler(w http.ResponseWriter, r *http.Request) {
	/*
		Used to handle a single request
	*/
	rawData := extractBody(w, r)
	// unmarshal the request input as ExtendedRequestInput
	params := ExtendedRequestInput{}
	err := json.Unmarshal(rawData, &params)
	if err != nil {
		http.Error(w, "Invalid JSON format for request", http.StatusBadRequest)
		return
	}
	// call the request function and write the response back to the client
	var jsonResponse []byte
	if params.WantHistory && params.RequestInput.FollowRedirects {
		// get full history
		historyResponses := requestHistory(&params)
		jsonResponse, err = json.Marshal(ResponseWrapper{History: *historyResponses, IsHistory: true})
	} else {
		// get single response
		response := request(&params)
		jsonResponse, err = json.Marshal(ResponseWrapper{Response: response, IsHistory: false})
	}

	if err != nil {
		http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
		return
	}
	w.Write(jsonResponse)
}

func multiRequestHandler(w http.ResponseWriter, r *http.Request) {
	rawData := extractBody(w, r)
	// unmarshal the request input as []ExtendedRequestInput
	requests := []ExtendedRequestInput{}
	err := json.Unmarshal(rawData, &requests)
	if err != nil {
		http.Error(w, "Invalid JSON format for multirequest", http.StatusBadRequest)
		return
	}

	results := make([]*ResponseWrapper, len(requests))
	resultsCh := make(chan *IndexedResponseWrapper, len(requests))
	var wg sync.WaitGroup

	for idx, param := range requests {
		param_ptr := param // create local pointer
		wg.Add(1)
		go func(i int, param_ptr *ExtendedRequestInput) {
			defer wg.Done()
			var resWrapper *ResponseWrapper
			if param_ptr.WantHistory && param_ptr.RequestInput.FollowRedirects {
				resWrapper = &ResponseWrapper{
					IsHistory: true,
					History:   *requestHistory(param_ptr),
				}
			} else {
				resWrapper = &ResponseWrapper{
					IsHistory: false,
					Response:  request(param_ptr),
				}
			}
			resultsCh <- &IndexedResponseWrapper{i, resWrapper}
		}(idx, &param_ptr)
	}

	// Wait for all goroutines to finish and close the results channel
	go func() {
		wg.Wait()
		close(resultsCh)
	}()

	// Collect results from the channel
	for indexedWrapper := range resultsCh {
		results[indexedWrapper.int] = indexedWrapper.ResponseWrapper
	}

	// Marshal the results into a JSON array
	resultsJson, err := json.Marshal(results)
	if err != nil {
		http.Error(w, "Failed to marshal results", http.StatusInternalServerError)
		return
	}

	// Write the response back to the client
	w.Write(resultsJson)
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	/*
		Returns "pong"
	*/
	w.Write([]byte("pong"))
}

func main() {
	/*
		Start the HTTP server
	*/
	if len(os.Args) < 2 {
		fmt.Println("Usage: <program-name> <port-number>")
		os.Exit(1)
	}

	port := os.Args[1] // port is passed as the first argument

	fmt.Printf("Starting server at http://localhost:%s\n", port)
	startServer(port)
}

func startServer(port string) {
	http.HandleFunc("/request", requestHandler)
	http.HandleFunc("/multirequest", multiRequestHandler)
	http.HandleFunc("/ping", pingHandler)
	err := http.ListenAndServe(":"+port, nil)
	if err != nil {
		fmt.Printf("Failed to start server: %v\n", err)
		os.Exit(1)
	}
}

//export StartServer
func StartServer(port string) {
	// exposed function to start the server in a goroutine
	go startServer(port)
}

//export DestroyAll
func DestroyAll() {
	tls_client_cffi.ClearSessionCache()
}

//export DestroySession
func DestroySession(sessionId string) {
	tls_client_cffi.RemoveSession(sessionId)
}

func mergeRelative(srcURL string, redirURL string) (string, error) {
	parsedRed, err := url.Parse(redirURL)
	if err != nil {
		return "", err
	}

	// If the redirect url already has a domain and scheme, return with no change
	if parsedRed.Host != "" && parsedRed.Scheme != "" {
		return redirURL, nil
	}

	parsedSrc, err := url.Parse(srcURL)
	if err != nil {
		return "", err
	}

	// Rebuild with missing scheme and host
	if parsedRed.Scheme == "" {
		parsedRed.Scheme = parsedSrc.Scheme
	}
	if parsedRed.Host == "" {
		parsedRed.Host = parsedSrc.Host
	}

	return parsedRed.String(), nil
}

func requestHistory(requestInput *ExtendedRequestInput) *[]*tls_client_cffi.Response {
	// set follow redirects to false
	requestInput.RequestInput.FollowRedirects = false
	// create a list of requests
	// then while the response is a redirect, add the next request to the list
	// then return the list
	var requests []*tls_client_cffi.Response
	var responseJson *tls_client_cffi.Response

	for true {
		responseJson = request(requestInput)
		// add a copy of responseJson to requests
		requests = append(requests, responseJson)

		// if the response is not a redirect, then finish
		if responseJson.Status < 300 || responseJson.Status > 399 {
			break
		}
		// check the Location header
		location := responseJson.Headers["Location"][0]
		// merge the location with the original url
		newUrl, err := mergeRelative(requestInput.RequestInput.RequestUrl, location)
		if err != nil {
			break
		}

		// update the url in the request
		requestInput.RequestInput.RequestUrl = newUrl
		// merge cookies from responseJson into requestInput if they dont exist
		for key, value := range responseJson.Cookies {
			responseJson.Cookies[key] = value
		}
	}
	// marshal
	return &requests
}

func request(requestInput *ExtendedRequestInput) *tls_client_cffi.Response {
	tlsClient, sessionId, withSession, err := tls_client_cffi.CreateClient(requestInput.RequestInput)
	if err != nil {
		return handleErrorResponse(sessionId, withSession, err)
	}

	req, err := tls_client_cffi.BuildRequest(requestInput.RequestInput)
	if err != nil {
		clientErr := tls_client_cffi.NewTLSClientError(err)

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	cookies := buildCookies(requestInput.RequestInput.RequestCookies)

	if len(cookies) > 0 {
		tlsClient.SetCookies(req.URL, cookies)
	}

	resp, reqErr := tlsClient.Do(req)

	if reqErr != nil {
		clientErr := tls_client_cffi.NewTLSClientError(fmt.Errorf("failed to do request: %w", reqErr))

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	if resp == nil {
		clientErr := tls_client_cffi.NewTLSClientError(fmt.Errorf("response is nil"))

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	targetCookies := tlsClient.GetCookies(resp.Request.URL)

	response, err := tls_client_cffi.BuildResponse(sessionId, withSession, resp, targetCookies, requestInput.RequestInput)
	if err != nil {
		return handleErrorResponse(sessionId, withSession, err)
	}

	return &response
}

func handleErrorResponse(sessionId string, withSession bool, err *tls_client_cffi.TLSClientError) *tls_client_cffi.Response {
	response := tls_client_cffi.Response{
		Id:      uuid.New().String(),
		Status:  0,
		Body:    err.Error(),
		Headers: nil,
		Cookies: nil,
	}

	if withSession {
		response.SessionId = sessionId
	}

	return &response
}

func buildCookies(cookies []tls_client_cffi.Cookie) []*http.Cookie {
	var ret []*http.Cookie

	for _, cookie := range cookies {
		ret = append(ret, &http.Cookie{
			Name:    cookie.Name,
			Value:   cookie.Value,
			Path:    cookie.Path,
			Domain:  cookie.Domain,
			Expires: cookie.Expires.Time,
		})
	}

	return ret
}

func transformCookies(cookies []*http.Cookie) []tls_client_cffi.Cookie {
	var ret []tls_client_cffi.Cookie

	for _, cookie := range cookies {
		ret = append(ret, tls_client_cffi.Cookie{
			Name:   cookie.Name,
			Value:  cookie.Value,
			Path:   cookie.Path,
			Domain: cookie.Domain,
			Expires: tls_client_cffi.Timestamp{
				Time: cookie.Expires,
			},
		})
	}

	return ret
}
