class StackUnderFlow(ValueError):
    pass


class Sstack(object):
    def __init__(self):
        self.stack = []

    def push(self, elem):
        self.stack.append(elem)

    def pop(self):
        if self.stack == []:
            raise StackUnderFlow
        else:
            return self.stack.pop()

    def top(self):
        if self.stack == []:
            raise StackUnderFlow
        else:
            return self.stack[-1]

    def is_empty(self):
        return self.stack == []


def parensMatch(text):
    parens = "()[]{}"
    opneParens = "([{"
    closeParensDict = {')': '(', ']': '[', '}': '{'}

    def paren(text):
        i = 0
        len_text = len(text)
        while i < len_text:
            if (text[i] not in parens):
                i += 1
            else:
                yield text[i], i
                i += 1

    st = Sstack()
    for pr, i in paren(text):
        if pr in opneParens:
            st.push((pr, i))
        elif st.pop()[0] != closeParensDict[pr]:
            print('this paren %s (id: %d)is not matched' % (pr, i))
        else:
            print('Paren %s (id: %d)Matched' % (pr, i))


def main():
    text = '(1+2)*{3*[5+4*(2+8)]}'
    parensMatch(text)


if __name__ == '__main__':
    main()
