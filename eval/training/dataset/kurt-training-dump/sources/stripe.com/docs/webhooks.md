---
title: Registrieren Sie Stripe-Ereignisse in Ihrem Webhook-Endpoint
url: https://docs.stripe.com/webhooks?locale=de-DE
hostname: stripe.com
description: Erstellen Sie ein Ereignisziel, um Ereignisse an einem HTTPS-Webhook-Endpoint zu empfangen. Der Empfang von Webhook-Ereignissen ist besonders nützlich, um asynchrone Ereignisse zu überwachen, z. B. wenn die Bank eines Kunden/einer Kundin eine Zahlung bestätigt, ein Kunde/eine Kundin eine Zahlung anficht, eine wiederkehrende Zahlung erfolgreich ist oder wenn Sie Abonnementzahlungen einziehen.
sitename: docs.stripe.com
date: 2025-12-19
---
# Registrieren Sie Stripe-Ereignisse in Ihrem Webhook-Endpoint

## Hören Sie auf Ihrem Webhook-Endpoint auf Ereignisse in Ihrem Stripe-Konto, damit Ihre Integration automatisch Reaktionen auslösen kann.

#### Ereignisse an Ihr AWS-Konto senden

Sie können Ereignisse jetzt direkt an [Amazon EventBridge als Ereignisziel](https://stripe.com/event-destinations/eventbridge) senden.

Erstellen Sie ein Ereignisziel, um Ereignisse an einem HTTPS-Webhook-Endpoint zu empfangen. Nach der Registrierung eines Webhook-Endpoints kann Stripe Ereignisdaten in Echtzeit an den Webhook-Endpoint Ihrer Anwendung senden, wenn in Ihrem Stripe-Konto [Ereignisse](https://stripe.com/event-destinations#events-overview) stattfinden. Stripe verwendet HTTPS, um Webhook-Ereignisse als JSON-Nutzlast, die ein [Ereignisobjekt](https://stripe.com/api/events) enthält, an Ihre App zu senden.

Der Empfang von Webhook-Ereignissen hilft Ihnen, auf asynchrone Ereignisse zu reagieren, z.B. wenn die Bank eines Kunden/einer Kundin eine Zahlung bestätigt, ein Kunde/eine Kundin eine Zahlungsanfechtung einleitet oder eine wiederkehrende Zahlung erfolgreich ist.

## Loslegen

So empfangen Sie Webhook-Ereignisse in Ihrer App:

- Erstellen Sie einen Webhook-Endpoint-Handler, um POST-Anfragen für Ereignisdaten zu empfangen.
- Testen Sie Ihren Webhook-Endpoint-Handler lokal mit der Stripe CLI.
- Erstellen Sie ein neues
[Ereignisziel](https://stripe.com/event-destinations)für Ihren Webhook-Endpoint. - Sichern Sie Ihren Webhook-Endpoint.

Sie können einen Endpoint registrieren und erstellen, um mehrere verschiedene Ereignistypen auf einmal zu verarbeiten, oder individuelle Endpoints für bestimmte Ereignisse einrichten.

## Nicht unterstütztes Ereignistypverhalten für Organisationsereignisziele

Stripe sendet die meisten Ereignistypen asynchron, wartet aber bei einigen Ereignistypen auf eine Antwort. In diesen Fällen verhält sich Stripe unterschiedlich, je nachdem, ob das Ereignisziel antwortet oder nicht.

Wenn Ihr Ereignisziel [Organisations-](https://stripe.com/get-started/account/orgs)Ereignisse empfängt, besitzen diejenigen, die eine Antwort erfordern, die folgenden Einschränkungen:

- Sie können
`issuing_`

für Organisationsziele nicht abonnieren. Richten Sie stattdessen einenauthorization. request [Webhook-Endpoint](https://stripe.com/webhooks#example-endpoint)in einem Stripe-Konto innerhalb der Organisation ein, um diesen Ereignistyp zu abonnieren. Verwenden Sie`issuing_`

, um Kaufanfragen in Echtzeit zu autorisieren.authorization. request - Organisationsziele, die
`checkout_`

empfangen, können nichtsessions. completed [mit dem Weiterleitungsverhalten](https://stripe.com/checkout/fulfillment#redirect-hosted-checkout)umgehen, wenn Sie[Checkout](https://stripe.com/payments/checkout)direkt in Ihre Website einbetten oder Kunden/Kundinnen auf eine von Stripe gehostete Bezahlseite umleiten. Um das Weiterleitungsverhalten von Checkout zu beeinflussen, verarbeiten Sie diesen Ereignistyp mit einem[Webhook Endpoint](https://stripe.com/webhooks#example-endpoint), der in einem Stripe-Konto innerhalb der Organisation konfiguriert ist. - Organisationsziele, die erfolglos auf ein
`invoice.`

-Ereignis reagieren, können dencreated [automatischen Rechnungsabschluss nicht beeinflussen, wenn Sie den automatischen Einzug](https://stripe.com/billing/subscriptions/webhooks#understand)verwenden. Sie müssen diesen Ereignistyp mit einem[Webhook-Endpoint](https://stripe.com/webhooks#example-endpoint)verarbeiten, der in einem Stripe-Konto innerhalb der Organisation konfiguriert ist, um den automatischen Abschluss der Rechnung auszulösen.


## Handler erstellen

Richten Sie eine HTTP- oder HTTPS-Endpoint-Funktion ein, die Webhook-Anfragen mit einer POST-Methode akzeptieren kann. Wenn Sie noch dabei sind, Ihre Endpoint-Funktion auf Ihrem lokalen Computer zu entwickeln, kann HTTP für diese verwendet werden. Nachdem sie öffentlich zugänglich ist, muss Ihre Webhook-Endpoint-Funktion HTTPS nutzen.

Richten Sie Ihre Endpoint-Funktion wie folgt ein:

- POST-Anfragen mit einer JSON-Nutzlast verarbeitet, die aus einem
[Ereignisobjekt](https://stripe.com/api/events/object)besteht. - Für
[Organisations-](https://stripe.com/get-started/account/orgs)Ereignis-Handler wird der Wert`context`

untersucht, um festzustellen, welches Konto in einem Unternehmen das Ereignis erzeugt hat, und dann der Header`Stripe-Context`

entsprechend dem Wert`context`

festgelegt. - Gibt schnell einen erfolgreichen Statuscode (
`2xx`

) zurück, bevor eine komplexe Logik angewendet wird, die eine Zeitüberschreitung verursachen könnte. Beispielsweise müssen Sie eine`200`

-Antwort zurückgeben, bevor Sie eine Kundenrechnung in Ihrem Buchhaltungssystem als bezahlt aktualisieren können.

#### Hinweis

- Verwenden Sie unseren
[interaktiven Webhook-Endpoint-Builder](https://stripe.com/webhooks/quickstart), um eine Webhook-Endpoint-Funktion in Ihrer Programmiersprache zu erstellen. - Ermitteln Sie in der Stripe-API-Dokumentation die
[Thin-Ereignisobjekte](https://stripe.com/api/v2/events/event-types)oder[Snapshot-Ereignisobjekte](https://stripe.com/api/events/object), die Ihr Webhook-Handler verarbeiten muss.

#### Beispiel-Endpoint

Bei diesem Codeausschnitt handelt es sich um eine Webhook-Funktion, die so konfiguriert ist, dass sie nach empfangenen Ereignissen sucht, das Ereignis verarbeitet und eine `200`

-Antwort zurückgibt. Verweisen Sie auf den [Snapshot](https://stripe.com/event-destinations#events-overview)-Ereignis-Handler, wenn Sie API v1-Ressourcen verwenden, und verweisen Sie auf den [Thin](https://stripe.com/event-destinations#events-overview)-Ereignis-Handler, wenn Sie API v2-Ressourcen verwenden.

#### Verwendet `context`



## Handler testen

Bevor Sie mit Ihrer Webhook-Endpoint-Funktion live gehen, empfehlen wir Ihnen, Ihre Anwendungsintegration zu testen. Konfigurieren Sie dazu einen lokalen Listener zum Senden von Ereignissen an Ihren lokalen Computer und senden Sie Testereignisse. Zum Testen müssen Sie die [CLI](https://stripe.com/stripe-cli) verwenden.

#### Ereignisse an einen lokalen Endpoint weiterleiten

Um Ereignisse an Ihren lokalen Endpoint weiterzuleiten, führen Sie den folgenden Befehl mit der [CLI](https://stripe.com/stripe-cli) aus und richten einen lokalen Listener ein. Das Flag `--forward-to`

sendet alle [Stripe-Ereignisse](https://stripe.com/cli/trigger#trigger-event) im in einer [Sandbox](https://stripe.com/sandboxes) an Ihren lokalen Webhook-Endpoint. Verwenden Sie die entsprechenden CLI-Befehle unten, je nachdem, ob Sie [Thin](https://stripe.com/event-destinations#events-overview) oder Snapshot-Ereignisse nutzen.

#### Hinweis

Sie können auch den Befehl `stripe listen`

ausführen, um Ereignisse in der [Stripe Shell](https://stripe.com/stripe-shell/overview) anzuzeigen, obwohl Sie keine Ereignisse von der Shell an Ihren lokalen Endpoint weiterleiten können.

Zu den nützlichen Konfigurationen, die Ihnen beim Testen mit Ihrem lokalen Listener helfen, gehören die folgenden:

- Um die Verifizierung des HTTPS-Zertifikats zu deaktivieren, verwenden Sie das optionale Flag
`--skip-verify`

. - Um nur bestimmte Ereignisse weiterzuleiten, verwenden Sie das optionale Flag
`--events`

und übergeben Sie eine durch Kommas getrennte Liste von Ereignissen.

- Um Ereignisse von dem öffentlichen Webhook-Endpoint, den Sie bereits bei Stripe registriert haben, an Ihren lokalen Webhook-Endpoint weiterzuleiten, verwenden Sie das optionale Flag
`--load-from-webhooks-api`

. Es lädt Ihren registrierten Endpoint, analysiert den Pfad und die registrierten Ereignisse und hängt dann den Pfad an Ihren lokalen Webhook-Endpoint im`--forward-to path`

an.

- Verwenden Sie zum Überprüfen von Webhook-Signaturen
`{{WEBHOOK_`

aus der ursprünglichen Ausgabe des Befehls „listen“.SIGNING_ SECRET}}

`Ready! Your webhook signing secret is '{{WEBHOOK_SIGNING_SECRET}}' (^C to quit)`


#### Auslösen von Testereignissen

Um Testereignisse zu senden, lösen Sie einen Ereignistyp aus, den Ihr Ereignisziel abonniert hat, indem Sie manuell ein Objekt im Stripe-Dashboard erstellen. Erfahren Sie, wie Sie Ereignisse mit [Stripe für VS-Code](https://stripe.com/stripe-vscode) auslösen können.


## Ihren Endpoint registrieren

Nachdem Sie Ihre Webhook-Endpoint-Funktion getestet haben, verwenden Sie die [API](https://stripe.com/api/v2/event-destinations) oder die Registerkarte **Webhooks** in Workbench zum Registrieren der URL Ihres Webhook-Endpoints, um sicherzustellen, dass weiß, wohin Ereignisse gesendet werden sollen. Sie können bis zu 16 Webhook-Endpoints bei Stripe registrieren. Registrierte Webhook-Endpoints müssen öffentlich zugängliche **HTTPS**-URLs sein.

#### Webhook-URL-Format

Das URL-Format zum Registrieren eines Webhook-Endpoints ist:

`https://<your-website>/<your-webhook-endpoint>`


Wenn Ihre Domain beispielsweise `https://mycompanysite.`

ist und die Route zu Ihrem Webhook-Endpoint `@app.`

lautet, geben Sie `https://mycompanysite.`

als **Endpoint-URL** an.

#### Ein Ereignisziel für Ihren Webhook-Endpoint erstellen

Erstellen Sie ein Ereignisziel mit Workbench im Dashboard oder programmgesteuert mit der [API](https://stripe.com/api/v2/event-destinations). Sie können bis zu 16 Ereignisziele für jedes Stripe-Konto registrieren.

#### Hinweis

[Workbench](https://stripe.com/workbench) ersetzt das bestehende [Entwickler-Dashboard](https://stripe.com/development/dashboard). Wenn Sie immer noch das Entwickler-Dashboard verwenden, finden Sie hier weitere Informationen zum [Erstellen eines neuen Webhook-Endpoints](https://stripe.com/development/dashboard/webhooks).


## Endpoint sichern

Nachdem Sie bestätigt haben, dass Ihr Endpoint wie erwartet funktioniert, sichern Sie ihn, indem Sie [Best Practices für Webhooks](https://stripe.com/webhooks#best-practices) implementieren.

Sichern Ihre Integration, indem Sie dafür sorgen, dass Ihr Handler verifiziert, dass alle Webhook-Anfragen von Stripe generiert wurden. Sie können Webhook-Signaturen mit unseren offiziellen Bibliotheken verifizieren oder manuell.

## Webhook-Integrationen debuggen

Bei der Übermittlung von Ereignissen an Ihren Webhook-Endpoint können mehrere Arten von Problemen auftreten:

- Stripe kann ein Ereignis möglicherweise nicht an Ihren Webhook-Endpoint übermitteln.
- Bei Ihrem Webhook-Endpoint besteht möglicherweise ein SSL-Problem.
- Ihre Netzwerkverbindung ist unterbrochen.
- Ihr Webhook-Endpoint empfängt die von Ihnen erwarteten Ereignisse nicht.

### Ereignisübermittlungen anzeigen

Um die Zustellungen von Events anzuzeigen, wählen Sie den Webhook-Endpoint unter **Webhooks** aus und klicken Sie anschließend auf die Registerkarte **Events**. Auf der Registerkarte **Events** finden Sie eine Liste der Events und den Status `Delivered`

, `Pending`

oder `Failed`

. Klicken Sie auf ein Event, um die Metadaten anzuzeigen, darunter den HTTP-Statuscode des Zustellversuchs und den Zeitpunkt ausstehender zukünftiger Zustellungen.

Sie können auch die [Stripe-CLI](https://stripe.com/stripe-cli) verwenden, um direkt in Ihrem Datenterminal [Ereignisse zu überwachen](https://stripe.com/webhooks#test-webhook).

### HTTP-Statuscodes korrigieren

Wenn ein Ereignis den Statuscode `200`

anzeigt, bedeutet dies eine erfolgreiche Zustellung an den Webhook-Endpoint. Möglicherweise erhalten Sie auch einen anderen Statuscode als `200`

. In der folgenden Tabelle finden Sie eine Liste gängiger HTTP-Statuscodes und empfohlener Lösungen.

| Webhook-Status ausstehend | Beschreibung | Korrigieren |
|---|---|---|
| (Verbindung nicht möglich) FHLR | Wir können keine Verbindung zum Zielserver herstellen. | Stellen Sie sicher, dass Ihre Host-Domain im Internet öffentlich zugänglich ist. |
(`302` ) FHLR (oder ein anderer `3xx` -Status) | Der Zielserver hat versucht, die Anfrage an einen anderen Standort umzuleiten. Wir betrachten Weiterleitungsantworten auf Webhook-Anfragen als fehlgeschlagen. | Legen Sie das Webhook-Endpoint-Ziel auf die durch die Weiterleitung aufgelöste URL fest. |
(`400` ) FHLR (oder ein anderer `4xx` -Status) | Der Zielserver kann oder wird die Anfrage nicht verarbeiten. Dies kann vorkommen, wenn der Server einen Fehler erkennt (`400` ), wenn für die Ziel-URL Zugriffsbeschränkungen gelten (`401` , `403` ) oder wenn die Ziel-URL nicht existiert (`404` ). |
|
(`500` ) FHLR (oder ein anderer `5xx` -Status) | Bei der Verarbeitung der Anfrage ist auf dem Zielserver ein Fehler aufgetreten. | Überprüfen Sie die Protokolle Ihrer Anwendung, um zu verstehen, warum der Fehler `500` zurückgegeben wird. |
| (TLS-Fehler) FHLR | Wir konnten keine sichere Verbindung zum Zielserver herstellen. Diese Fehler werden in der Regel durch Probleme mit dem SSL/TLS-Zertifikat oder einem Zwischenzertifikat in der Zertifikatskette des Zielservers verursacht. Stripe erfordert die
`v1.` oder neuer. |

[SSL-Servertest](https://www.ssllabs.com/ssltest/)durch, um Probleme zu finden, die diesen Fehler möglicherweise verursacht haben.## Verhaltensweisen der Ereignisübermittlung

In diesem Abschnitt erfahren Sie, welche Verhaltensweisen Sie in Bezug auf das Senden von Ereignissen durch Stripe an Ihren Webhook-Endpoint erwarten können.

### Automatische Wiederholungsversuche

Stripe versucht, Ereignisse mit einem exponentiellen Backoff im Live-Modus bis zu drei Tage an Ihr Ziel zu senden. Wann der nächste Wiederholungsversuch stattfinden wird, sofern zutreffend, sehen Sie auf der Registerkarte **Ereignisübermittlungen** Ihres Ereignisziels. Wir versuchen, Ereignisse, die in einer Sandbox erstellt wurde, innerhalb weniger Stunden dreimal zu übermitteln. Wenn Ihr Ziel bei unserem Wiederholungsversuch deaktiviert oder gelöscht wurde, unternehmen wir keine zukünftigen Wiederholungsversuche für dieses Ereignis. Wenn Sie ein Ereignisziel jedoch deaktivieren und wieder reaktivieren, bevor wir einen erneuten Versuch starten können, sehen Sie nach wie vor zukünftige Wiederholungsversuche.

### Manuelle Wiederholungsversuche

Es gibt zwei Möglichkeiten, Ereignisse manuell zu wiederholen:

- Klicken Sie im Stripe-Dashboard auf
**Erneut senden**, wenn Sie sich ein bestimmtes Ereignis ansehen. Dies funktioniert bis zu 15 Tage nach der Erstellung des Ereignisses. - Führen Sie mit der
[Stripe CLI](https://stripe.com/cli/events/resend)den Befehl`stripe events resend <event_`

aus. Dies funktioniert bis zu 30 Tage nach der Erstellung des Ereignisses.id> --webhook-endpoint=<endpoint_ id>

Durch das manuelle erneute Senden eines Ereignisses, das frühere Zustellungsfehler hatte, an einen Webhook-Endpoint wird das [automatische Wiederholungsverhalten](https://stripe.com#automatic-retries) von Stripe nicht verworfen. Automatische Wiederholungsversuche erfolgen immer noch, bis Sie auf einen davon mit einem `2xx`

Status-Code antworten.

### Anordnung von Ereignissen

Stripe garantiert die Übermittlung von Ereignissen nicht in der Reihenfolge, in der sie generiert wurden. Beim Erstellen eines Abonnements können beispielsweise die folgenden Ereignisse generiert werden:

`customer.`

subscription. created `invoice.`

created `invoice.`

paid `charge.`

(wenn eine Zahlung vorhanden ist)created

Stellen Sie sicher, dass Ihr Ereignisziel Ereignisse nicht nur in einer bestimmten Reihenfolge empfangen kann. Ihr Ziel sollte jegliche Übermittlung entsprechend verarbeiten können. Sie können fehlende Objekte auch mit der API abrufen. So können Sie beispielsweise die Objekte für Rechnung, Zahlung und Abonnement mit den Informationen aus `invoice.`

abrufen, wenn Sie dieses Ereignis zuerst erhalten.

### API-Versionierung

Die API-Version in Ihren Kontoeinstellungen beim Auftreten des Ereignisses bestimmt die API-Version und damit die Struktur eines [Ereignisses](https://stripe.com/api/events), das an Ihr Ziel gesendet wird. Wenn für Ihr Konto beispielsweise eine ältere API-Version festgelegt ist, z. B. 16.02.2015, und Sie die API-Version mit [Versionierung](https://stripe.com/api#versioning) für eine bestimmte Anfrage ändern, basiert das generierte und an Ihr Ziel gesendete [Ereignis](https://stripe.com/api/events)-Objekt weiterhin auf der API-Version 2015-02-16. Sie können [Ereignis](https://stripe.com/api/events)-Objekte nach der Erstellung nicht mehr ändern. Wenn Sie beispielsweise eine Zahlung aktualisieren, bleibt das ursprüngliche Zahlungsereignis unverändert. Nachfolgende Aktualisierungen der API-Version Ihres Kontos ändern daher vorhandene [Ereignis](https://stripe.com/api/events)-Objekte nicht rückwirkend. Auch das Abrufen eines älteren [Ereignisses](https://stripe.com/api/events) durch Aufrufen von `/v1/events`

mithilfe einer neueren API-Version wirkt sich nicht auf die Struktur des empfangenen Ereignisses aus. Sie können Testereignisziele entweder auf Ihre Standard-API-Version oder die neueste API-Version festlegen. Das an das Ziel gesendete [Ereignis](https://stripe.com/api/events) ist für die angegebene Version des Ereignisziels strukturiert.

## Best Practices für die Verwendung von Webhooks

Überprüfen Sie diese Best Practices, um sicherzustellen, dass Ihre Webhook-Endpoints sicher bleiben und gut mit Ihrer Integration funktionieren.

### Umgang mit doppelten Ereignissen

Webhook-Endpoints empfangen gelegentlich dasselbe Ereignis mehrmals. Sie können sich vor dem Erhalt doppelter Ereignisse schützen, indem Sie Ihre verarbeiteten [Ereignis-IDs](https://stripe.com/api/events/object#event_object-id) protokollieren und bereits protokollierte Ereignisse dann nicht erneut verarbeiten.

In einigen Fällen werden zwei separate Ereignisobjekte generiert und gesendet. Um diese Duplikate zu identifizieren, verwenden Sie die ID des Objekts in `data.`

zusammen mit dem `event.`

.

### Nur die Ereignistypen überwachen, die Ihre Integration erfordert

Konfigurieren Sie Ihre Webhook-Endpoints so, dass sie nur die für Ihre Integration erforderlichen Ereignistypen empfangen. Die Überwachung zusätzlicher Ereignisse (oder aller Ereignisse) belastet Ihren Server und wird nicht empfohlen.

Sie können [die Ereignisse](https://stripe.com/api/webhook_endpoints/update#update_webhook_endpoint-enabled_events), die ein Webhook-Endpoint empfängt, im Dashboard oder mit der API ändern.

### Ereignisse asynchron verarbeiten

Konfigurieren Sie Ihren Handler so, dass eingehende Ereignisse mit einer asynchronen Warteschlange verarbeitet werden. Möglicherweise treten Skalierbarkeitsprobleme auf, wenn Sie sich für die synchrone Verarbeitung von Ereignissen entscheiden. Jeder große Anstieg bei den Webhook-Übermittlungen (z. B. zu Beginn des Monats, wenn alle Abonnements verlängert werden) kann Ihre Endpoint-Hosts überfordern.

Asynchrone Warteschlangen ermöglichen es Ihnen, die gleichzeitigen Ereignisse mit einer Geschwindigkeit zu verarbeiten, die Ihr System unterstützen kann.

### Webhook-Route vom CSRF-Schutz ausgenommen

Wenn Sie Rails, Django oder ein anderes Web-Framework verwenden, überprüft Ihre Website möglicherweise automatisch, ob jede POST-Anfrage ein *CSRF-Token* enthält. Dies ist eine wichtige Sicherheitsfunktion, die Sie und Ihre Nutzer/innen vor [Cross-Site-Request-Forgery](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)) -Angriffen schützt. Diese Sicherheitsmaßnahme kann Ihre Website jedoch auch daran hindern, legitime Ereignisse zu verarbeiten. In diesem Fall müssen Sie möglicherweise die Webhooks-Route vom CSRF-Schutz ausnehmen.

### Ereignisse mit einem HTTPS-Server empfangen

Wenn Sie eine HTTPS-URL für Ihren Webhook-Endpoint verwenden (im Live-Modus erforderlich), validiert Stripe, dass die Verbindung zu Ihrem Server sicher ist, bevor wir Ihre Webhook-Daten senden. Damit dies funktioniert, muss der Server so konfiguriert sein, dass er HTTPS mit einem gültigen Server-Zertifikat unterstützt. Stripe-Webhooks unterstützen nur die [TLS](https://stripe.com/security/guide#tls)-Versionen v1.2 und v1.3.

### Geheimschlüssel für Signaturen für Endpoints in regelmäßigen Abständen neu generieren

Der Geheimschlüssel, der verwendet wird, um zu überprüfen, ob Ereignisse von Stripe stammen, kann auf der Registerkarte **Webhooks** in Workbench geändert werden. Um Geheimschlüssel zu schützen, empfehlen wir sie in regelmäßigen Abständen neu zu generieren (zu ändern) oder wenn Sie vermuten, dass ein Geheimschlüssel kompromittiert wurde.

So generieren Sie einen Geheimschlüssel neu:

- Klicken Sie auf die einzelnen Endpoints auf der Workbench-Registerkarte
**Webhooks**, für die Sie den Geheimschlüssel neu generieren möchten. - Navigieren Sie zum Überlaufmenü () und klicken Sie auf
**Geheimschlüssel neu generieren**. Sie können den aktuellen Geheimschlüssel sofort ablaufen lassen oder den Ablauf um bis zu 24 Stunden verzögern, damit Sie Zeit haben, den Verifizierungscode auf Ihrem Server zu aktualisieren. Während dieses Zeitraums sind mehrere Geheimschlüssel für den Endpoint aktiv. Stripe generiert bis zum Ablauf eine Signatur pro Geheimschlüssel.

### Überprüfen, ob Ereignisse von Stripe gesendet werden

Stripe sendet Webhook-Ereignisse von einer festgelegten Liste von IP-Adressen. Vertrauen Sie nur Ereignissen, die von diesen [IP-Adressen](https://stripe.com/ips) stammen.

Überprüfen Sie auch Webhook-Signaturen, um zu bestätigen, dass Stripe die empfangenen Ereignisse gesendet hat. Stripe signiert Webhook-Ereignisse, die an Ihre Endpoints gesendet werden, indem eine Signatur in den `Stripe-Signature`

-Header jedes Ereignisses eingefügt wird. So können Sie überprüfen, ob die Ereignisse von Stripe und nicht von einem Drittanbieter gesendet wurden. Sie können Signaturen entweder mit unseren [offiziellen Bibliotheken](https://stripe.com#verify-official-libraries) verifizieren oder mit Ihrer eigenen Lösung [manuell verifizieren](https://stripe.com#verify-manually).

Im folgenden Abschnitt wird beschrieben, wie Sie Webhook-Signaturen verifizieren:

- Rufen Sie den Geheimschlüssel Ihres Endpoints ab.
- Überprüfen Sie die Signatur.

#### Geheimschlüssel Ihres Endpoints abrufen

Verwenden Sie Workbench und gehen Sie auf die Registerkarte **Webhooks**, um alle Ihre Endpoints anzuzeigen. Wählen Sie einen Endpoint aus, für den Sie den Geheimschlüssel erfahren möchten, und klicken Sie dann auf **Klicken Sie zum Aufdecken**.

Stripe generiert für jeden Endpoint einen eindeutigen Geheimschlüssel. Wenn Sie denselben Endpoint sowohl für [Test- als auch für Live-API-Schlüssel](https://stripe.com/keys#test-live-modes) verwenden, ist der Geheimschlüssel für jeden dieser Schlüssel unterschiedlich. Wenn Sie mehrere Endpoints verwenden, müssen Sie außerdem für jeden Endpoint, für den Sie Signaturen verifizieren möchten, einen Geheimschlüssel abrufen. Nach dieser Einrichtung beginnt Stripe, jeden Webhook zu signieren, der an den Endpoint gesendet wird.

### Replay-Angriffe verhindern

Bei einem [Replay-Angriff](https://en.wikipedia.org/wiki/Replay_attack) fängt ein Angreifer eine gültige Nutzlast und deren Signatur ab und überträgt sie dann erneut. Um solche Angriffe zu verhindern, fügt Stripe einen Zeitstempel in den `Stripe-Signature`

-Header ein. Da der Zeitstempel zu der signierten Nutzlast gehört, ist er ebenfalls durch die Signatur verifiziert. So kann ein Angreifer den Zeitstempel nicht ändern, ohne dass die Signatur ungültig wird. Wenn die Signatur gültig, der Zeitstempel aber zu alt ist, kann Ihre Anwendung die Nutzlast ablehnen.

Unsere Bibliotheken haben eine Standardtoleranz von 5 Minuten zwischen dem Zeitstempel und der aktuellen Zeit. Sie können diese Toleranz ändern, indem Sie bei der Überprüfung von Signaturen einen zusätzlichen Parameter angeben. Verwenden Sie das Network Time Protocol ([NTP](https://en.wikipedia.org/wiki/Network_Time_Protocol)), um sicherzustellen, dass die Uhrzeit Ihres Servers korrekt ist und mit der Zeit auf den Servern von Stripe synchronisiert wird.

#### Häufiger Fehler

Verwenden Sie keinen Toleranzwert von `0`

.Mit einem Toleranzwert von `0`

wird die Aktualitätsprüfung vollständig deaktiviert.

Stripe generiert den Zeitstempel und die Signatur jedes Mal, wenn wir ein Ereignis an Ihren Endpoint senden. Wenn Stripe ein Ereignis wiederholt (zum Beispiel weil Ihr Endpoint zuvor mit einem Nicht-`2xx`

-Statuscode geantwortet hat), generieren wir eine neue Signatur und einen neuen Zeitstempel für den neuen Zustellungsversuch.

### Schnelle Rückgabe einer 2xx-Antwort

Ihr [Endpoint](https://stripe.com/webhooks#example-endpoint) muss schnell einen erfolgreichen Statuscode (`2xx`

) zurückgeben, bevor eine komplexe Logik angewendet wird, die eine Zeitüberschreitung verursachen könnte. Beispielsweise müssen Sie eine `200`

-Antwort zurückgeben, bevor Sie eine Kundenrechnung in Ihrem Buchhaltungssystem als bezahlt aktualisieren können.