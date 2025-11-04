import insert_1st as first
import insert_qpoll as qpoll
import insert_2nd as second
import drop_table as drop

if __name__ == "__main__":
    print("\n----------------------------------------\n")
    print(">>>테이블 초기화(DROP).\n")
    drop.drop_all_tables() #이때 모든 테이블을 DROP함으로 만일 삽입되어 있는 데이터가 있다면 주석처리 or 백업!
    print("\n----------------------------------------\n")
    print(">>>ETL 작업 시작.\n")
    print("\n----------------------------------------\n")
    first.main() #welcome_1st 삽입! 
    print("\n----------------------------------------\n")
    print(">>> Welcome 1st ETL 작업 완료.\n")
    print("----------------------------------------\n")
    qpoll.main() #qpoll ... 삽입!
    print("\n----------------------------------------\n")
    print(">>> qpoll_... ETL 작업 완료.\n")
    print("----------------------------------------\n")
    second.main() #welcome_2nd 삽입!
    print("\n----------------------------------------\n")
    print(">>> Welcome 2nd ETL 작업 완료.\n")
    print("----------------------------------------\n")