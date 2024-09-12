export const getAIMessage = async (userQuery) => {
  try {
    // Get the sessionId from sessionStorage
    const sessionId = sessionStorage.getItem("sessionId") || "";

    const url = new URL("http://localhost:8000/agent");
   // const url = new URL("https://case-study-3.onrender.com/agent");
    url.searchParams.append("message", userQuery);
    url.searchParams.append("session", sessionId);

    // Set request options
    const options = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    // Fetch the response
    const response = await fetch(url, options);

    // Handle non-OK responses
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Parse the response
    const data = await response.json();
    console.log("AI Response:", data);

    // Return the assistant message
    return {
      role: "assistant",
      content: data.response || "No response available",
    };
  } catch (error) {
    // Log the error for debugging purposes
    console.error("Error fetching AI message:", error);

    // Return a default error message
    return {
      role: "assistant",
      content: "Sorry, I couldn't process your request at this moment.",
    };
  }
};
