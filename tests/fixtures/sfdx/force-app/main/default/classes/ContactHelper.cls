public class ContactHelper {
    public static void touch(List<Contact> contacts) {
        for (Contact c : contacts) {
            c.LastModifiedDate = System.now();
        }
    }
}
