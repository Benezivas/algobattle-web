
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

export async function send_get(action, content) {
    var _content = {
        "method": "GET",
    }
    var params = ""
    if (content != undefined) {
        params = "?" + new URLSearchParams(content).toString()
    }
    var response = await fetch("/api/" + action + params, _content)
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

export function remove_unchanged(payload, object) {
    for (const [key, val] of payload.entries()) {
        if (val == object[key] || val == undefined) {
            payload.delete(key)
        }
    }
}

export function pick(obj, ...keys){
    return Object.fromEntries(
        keys
        .filter(key => key in obj)
        .map(key => [key, obj[key]])
      );
}

export function inclusive_pick(obj, ...keys) {
    return Object.fromEntries(
    	    keys.map(key => [key, obj[key]])
    )
}

export function omit(obj, ...keys) {
    return Object.fromEntries(
        Object.entries(obj)
        .filter(([key]) => !keys.includes(key))
    )
}

export function queryParams() {
    const params = new URLSearchParams(window.location.search)
    return Object.fromEntries(params.entries())
}
