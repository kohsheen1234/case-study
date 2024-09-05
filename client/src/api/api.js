export const getAIMessage = async (userQuery) => {
  try {
    const sessionId = sessionStorage.getItem("sessionId") || "";

    const response = await fetch(
      `http://localhost:8000/agent?message=${encodeURIComponent(
        userQuery
      )}&session=${encodeURIComponent(sessionId)}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    const data = await response.json();
    console.log("AI Response: ", data);

    const message = {
      role: "assistant",
      content: data.response,
    };

    return message;
  } catch (error) {
    console.error("Error fetching AI message: ", error);

    // Return a fallback message in case of an error
    return {
      role: "assistant",
      content: "Sorry, I couldn't process your request at this moment.",
    };
  }
};
