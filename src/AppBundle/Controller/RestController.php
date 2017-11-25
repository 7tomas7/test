<?php

namespace AppBundle\Controller;

use AppBundle\Entity\User;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Route;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Method;
use Symfony\Bundle\FrameworkBundle\Controller\Controller;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Security\Core\Encoder\UserPasswordEncoderInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\Serializer\Serializer;
use Symfony\Component\Serializer\Encoder\JsonEncoder;
use Symfony\Component\Serializer\Normalizer\ObjectNormalizer;
use \Symfony\Component\HttpFoundation\Response;

/**
 * @Route("/rest")
 */
class RestController extends Controller {

    /**
     * @Route("/retrieve", name="rest_retrieve_user")
     * @Method("GET")
     */
    public function retrieveAction(Request $request, UserPasswordEncoderInterface $passwordEncoder) {

        $encoders = array(new JsonEncoder());
        $normalizers = array(new ObjectNormalizer());
        $serializer = new Serializer($normalizers, $encoders);

        $username = $request->get('username');
        $user = $this->getDoctrine()
                        ->getRepository('AppBundle:User')->findOneBy(array('username' => $username));

        if (!$user) {
            return new JsonResponse("Nie ma takiego usera");
        }

        $jsonUser = $serializer->serialize($user, 'json');

        return new Response($jsonUser);
    }

    /**
     * @Route("/add", name="rest_add_user")
     * @Method("POST")
     */
    public function addAction(Request $request, UserPasswordEncoderInterface $passwordEncoder) {

        $data = json_decode($request->getContent(), true);

        //ponizej jakies walidacje w zaleznosci od tego co kto potrzebuje i jaki ktos chce ten JSON, można też w formularz wsadzić walidacje

        if (!$data['user']['email'] || !$data['user']['password'] || !$data['user']['username']) {
            return new JsonResponse("Brak wszystkich poprawnych danych");
        }

        try {
            $user = new User();
            $user->setEmail($data['user']['email']);
            $user->setPassword($data['user']['password']);
            $user->setUsername($data['user']['username']);

            $passwordCoded = $passwordEncoder->encodePassword($user, $user->getPassword());
            $user->setPassword($passwordCoded);
            $em = $this->getDoctrine()->getManager();
            $em->persist($user);
            $em->flush();
            return new JsonResponse("Użytkownik dodany");
        } catch (\Exception $em) {
            return new JsonResponse("Użytkownik nie dodany");
        }
    }

    /**
     * @Route("/edit", name="rest_edit_user")
     * @Method("PUT")
     */
    public function editAction(Request $request, UserPasswordEncoderInterface $passwordEncoder) {

        $data = json_decode($request->getContent(), true);
        $username = array_keys($data)[0];

        $user = $this->getDoctrine()
                        ->getRepository('AppBundle:User')->findOneBy(array('username' => $username));
        if (!$user) {
            return new JsonResponse("Nie ma takiego usera");
        }
        //ponizej jakies walidacje w zaleznosci od tego co kto potrzebuje i jaki ktos chce ten JSON, lub w formualrz dac dane

        if (!$data[$username]['email'] || !$data[$username]['password'] || !$data[$username]['username']) {
            return new JsonResponse("Brak wszystkich poprawnych danych");
        }

        $user->setEmail($data[$username]['email']);
        $user->setPassword($data[$username]['password']);
        $user->setUsername($data[$username]['username']);

        $passwordCoded = $passwordEncoder->encodePassword($user, $user->getPassword());
        $user->setPassword($passwordCoded);

        try {
            $em = $this->getDoctrine()->getManager();
            $em->flush();
            return new JsonResponse("Użytkownik zaktualizowany");
        } catch (\Exception $em) {
            return new JsonResponse("Użytkownik nie zaktualizowana, bo np się powtarza czy coś");
        }
    }

    /**
     * @Route("/delete", name="rest_delete_user")
     * @Method("DELETE")
     */
    public function deleteAction(Request $request) {

        $data = json_decode($request->getContent(), true);
        $username = $data['username'];

        $user = $this->getDoctrine()
                        ->getRepository('AppBundle:User')->findOneBy(array('username' => $username));
        if (!$user) {
            return new JsonResponse("Nie ma takiego usera");
        }
        $em = $this->getDoctrine()->getManager();
        $em->remove($user);
        $em->flush();

        return new JsonResponse("Użytkownik usuniety");
    }

}
