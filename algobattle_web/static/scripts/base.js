
export async function send_request(action, content) {
    var _content = {
        "method": "POST",
    }
    if (content != undefined) {
        _content.headers = {"Content-type": "application/json"}
        _content.body = JSON.stringify(content)
    }
    var response = await fetch("/api/" + action, _content)
    if (response.ok) {
        return response.json()
    }
}

export async function send_form(endpoint, content) {
    var response = await fetch("/api/" + endpoint, {
        "method": "POST",
        "body": content,
    })
    if (response.ok) {
        return response
    }
}

export function fmt_date(date) {
    if (!date) {
        return ""
    }
    date = new Date(date)
    return date.toLocaleString()
}
