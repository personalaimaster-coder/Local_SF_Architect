public class OrderProcessor {
    public void run() {
        AccountService service = new AccountService();
        service.process(null);
    }
}
