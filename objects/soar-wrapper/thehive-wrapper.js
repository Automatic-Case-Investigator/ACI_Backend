import SOARWrapper from "./soar-wrapper.js";

class TheHiveWrapper extends SOARWrapper {
    constructor(url, apiKey) {
        super(url, apiKey);
    }

    async getCase(caseId) {
        const urlObj = new URL(this.url);
        const response = await fetch(
            `${urlObj.protocol}//${urlObj.host}/api/v1/case/${caseId}`,
            {
                headers:
                {
                    "Accept": "*/*",
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${this.apiKey}`
                }
            }
        );
        return await response.json();
    }
}

export default TheHiveWrapper;