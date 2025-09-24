//TIP 코드를 <b>실행</b>하려면 <shortcut actionId="Run"/>을(를) 누르거나
// 에디터 여백에 있는 <icon src="AllIcons.Actions.Execute"/> 아이콘을 클릭하세요.
public class Main {
    public static void main(String[] args) {
        Person person = new Person("홍길동");
        Phone phone1 = new Phone("010-1234-5678");
        Phone phone2 = new Phone("02-123-1234");
        Phone phone3 = new Phone("010-2345-6789");
        person.addPhone(phone1);
        person.addPhone(phone2);
        person.addPhone(phone3);
    }
}